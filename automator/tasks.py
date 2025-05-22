import decimal
from web3 import Web3
from web3.exceptions import Web3RPCError
import datetime

from .contracts import MocCARC20, MocCACoinbase, MoCMedianizer, CommissionSplitter, PriceProvider, MocMultiCollateralGuard

from .base.main import ConnectionHelperBase
from .base.token import ERC20Token
from .tasks_manager import PendingTransactionsTasksManager, on_pending_transactions
from .logger import log
from .utils import aws_put_metric_heart_beat


__VERSION__ = '1.0.10'


log.info("Starting Stable Protocol Automator version {0}".format(__VERSION__))


class Automator(PendingTransactionsTasksManager):

    def __init__(self,
                 config,
                 connection_helper,
                 contracts_loaded
                 ):
        self.config = config
        self.connection_helper = connection_helper
        self.contracts_loaded = contracts_loaded

        # init PendingTransactionsTasksManager
        super().__init__(self.config,
                         self.connection_helper,
                         self.contracts_loaded)

    def info_tx(self):

        web3 = self.connection_helper.connection_manager.web3

        nonce = web3.eth.get_transaction_count(
            self.connection_helper.connection_manager.accounts[0].address, "pending")

        # get gas price from node
        node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

        # Multiply factor of the using gas price
        calculated_gas_price = node_gas_price * decimal.Decimal(self.config['gas_price_multiply_factor'])
        max_fee_per_gas = None
        if max_fee_per_gas in self.config:
            max_fee_per_gas = self.config['max_fee_per_gas']
        max_priority_fee_per_gas = None
        if max_priority_fee_per_gas in self.config:
            max_priority_fee_per_gas = self.config['max_priority_fee_per_gas']

        return dict(
            nonce=nonce,
            calculated_gas_price=calculated_gas_price,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    def is_valid_tp_price(self):
        valid = True
        for pp in self.contracts_loaded["PriceProviders"]:
            price_item = pp.peek()
            valid = price_item[1]
            if not valid:
                break
        return valid

    @on_pending_transactions
    def calculate_ema(self, index, task=None, global_manager=None, task_result=None):

        contract_moc = self.contracts_loaded["Moc"][index]
        if contract_moc.sc.functions.shouldCalculateEma().call():

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            # check if is valid price before send
            if not self.is_valid_tp_price():
                log.error("Task :: {0} :: Error not valid TP price provider!".format(task.task_name))
                return

            info_transaction = self.info_tx()

            try:
                tx_hash = contract_moc.update_emas(
                    gas_limit=self.config['tasks']['calculate_ema']['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = self.config['tasks']['calculate_ema']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def execute_settlement(self, index, task=None, global_manager=None, task_result=None):

        contract_moc = self.contracts_loaded["Moc"][index]

        web3 = self.connection_helper.connection_manager.web3
        last_block_timestamp = web3.eth.get_block(web3.eth.block_number).timestamp

        # Get if block to settlement > 0 to continue
        next_settlement_time = contract_moc.sc.functions.nextSettlementTime().call()

        if next_settlement_time < last_block_timestamp:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            # check if is valid price before send
            if not self.is_valid_tp_price():
                log.error("Task :: {0} :: Error not valid TP price provider!".format(task.task_name))
                return

            info_transaction = self.info_tx()

            try:
                tx_hash = contract_moc.execute_settlement(
                    gas_limit=self.config['tasks']['execute_settlement']['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = self.config['tasks']['execute_settlement']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def tc_holders_interest_payment(self, index, task=None, global_manager=None, task_result=None):

        contract_moc = self.contracts_loaded["Moc"][index]

        web3 = self.connection_helper.connection_manager.web3
        last_block_timestamp = web3.eth.get_block(web3.eth.block_number).timestamp

        next_payment_time = contract_moc.sc.functions.nextTCInterestPayment().call()
        if next_payment_time < last_block_timestamp:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            # check if is valid price before send
            if not self.is_valid_tp_price():
                log.error("Task :: {0} :: Error not valid TP price provider!".format(task.task_name))
                return

            info_transaction = self.info_tx()

            try:
                tx_hash = contract_moc.tc_holders_interest_payment(
                    gas_limit=self.config['tasks']['tc_holders_interest_payment']['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = self.config['tasks']['tc_holders_interest_payment']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def oracle_poke(self, task=None, global_manager=None, task_result=None):

        price_validity = self.contracts_loaded["MoCMedianizer"].sc.functions.peek().call()[1]
        if not self.contracts_loaded["MoCMedianizer"].sc.functions.compute().call()[1] and price_validity:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            info_transaction = self.info_tx()

            try:
                tx_hash = self.contracts_loaded["MoCMedianizer"].poke(
                    gas_limit=self.config['tasks']['oracle_poke']['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = self.config['tasks']['oracle_poke']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

            log.error("Task :: {0} :: Not valid price! Disabling Price!".format(task.task_name))
            aws_put_metric_heart_beat(self.config['tasks']['oracle_poke']['cloudwatch'], 1)

        else:
            # if no valid price in oracle please send alarm
            if not price_validity:
                log.error("Task :: {0} :: No valid price in oracle!".format(task.task_name))
                aws_put_metric_heart_beat(self.config['tasks']['oracle_poke']['cloudwatch'], 1)

            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def commission_splitter(self, index, task=None, global_manager=None, task_result=None):

        commission_setting = self.config['tasks']['commission_splitters'][index]

        token_balance = self.contracts_loaded[
            "CommissionSplitter_Token_{0}".format(index)].sc.functions.balanceOf(commission_setting["address"]).call()

        fee_token_balance = 0
        if commission_setting["fee_token"]:
            fee_token_balance = self.contracts_loaded[
                "CommissionSplitter_FeeToken_{0}".format(index)].sc.functions.balanceOf(
                commission_setting["address"]).call()

        if token_balance > commission_setting["min_balance"] or \
                fee_token_balance > commission_setting["min_balance_fee_token"]:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            log.info("Task :: {0} :: Commission Splitter has balance!. Balances: -AC Token: {1}. -Fee Token: {2}.  ".format(
                task.task_name,
                Web3.from_wei(token_balance, 'ether'),
                Web3.from_wei(fee_token_balance, 'ether')))

            info_transaction = self.info_tx()

            try:
                tx_hash = self.contracts_loaded["CommissionSplitter_{0}".format(index)].split(
                    gas_limit=commission_setting['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = commission_setting['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def refresh_ac_balance(self, index, index_token, task=None, global_manager=None, task_result=None):

        contract_moc = self.contracts_loaded["Moc"][index]
        contract_token = self.contracts_loaded["CA_TOKEN"][index_token]

        ac_balance = contract_token.balance_of(contract_moc.contract_address)
        ac_balance_collateral_bag = Web3.from_wei(contract_moc.ac_balance_collateral_bag(), 'ether')
        locked_in_pending = Web3.from_wei(contract_moc.locked_in_pending(), 'ether')

        if ac_balance > ac_balance_collateral_bag + locked_in_pending:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            info_transaction = self.info_tx()

            try:
                tx_hash = contract_moc.refresh_ac_balance(
                    gas_limit=self.config['tasks']['refresh_ac_balance']['gas_limit'],
                    gas_price=int(info_transaction['calculated_gas_price'] * 10 ** 18),
                    max_fee_per_gas=info_transaction['max_fee_per_gas'],
                    max_priority_fee_per_gas=info_transaction['max_priority_fee_per_gas'],
                    nonce=info_transaction['nonce']
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = info_transaction['calculated_gas_price']
                new_tx['nonce'] = info_transaction['nonce']
                new_tx['timeout'] = self.config['tasks']['refresh_ac_balance']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(info_transaction['calculated_gas_price'] * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result


MAX_AC_AVAILABLE = 2
MAX_TP_RANGE = 4


class AutomatorTasks(Automator):

    def __init__(self, config):

        self.config = config
        self.connection_helper = ConnectionHelperBase(config)

        self.contracts_loaded = dict()
        self.contracts_addresses = dict()
        self.moc_buckets_addresses = []

        # contract addresses
        self.load_contracts()

        # init automator
        super().__init__(self.config,
                         self.connection_helper,
                         self.contracts_loaded)

        # Add tasks
        self.schedule_tasks()

    def load_contracts(self):
        """ Get contract address to use later """

        log.info("Getting addresses from Main Contract...")

        # Multi-collateral MOC
        log.info("MocMultiCollateralGuard using address: %s" % self.config['addresses']['MocMultiCollateralGuard'])
        # MocMultiCollateralGuard
        self.contracts_loaded["MocMultiCollateralGuard"] = MocMultiCollateralGuard(
            self.connection_helper.connection_manager,
            contract_address=self.config['addresses']['MocMultiCollateralGuard'])
        self.contracts_addresses['MocMultiCollateralGuard'] = self.contracts_loaded[
            "MocMultiCollateralGuard"].address().lower()

        # Reading MoC Buckets from Multi collateral Guard
        self.moc_buckets_addresses = []
        self.contracts_loaded['Moc'] = []
        self.contracts_loaded["CA_TOKEN"] = []
        for ca_index, ca in enumerate(self.config['collateral']):
            try:
                moc_bucket_address = self.contracts_loaded["MocMultiCollateralGuard"].buckets(ca_index)
            except Web3RPCError:
                continue

            contract_interface = MocCACoinbase
            if ca['type'] == 'rc20':
                contract_interface = MocCARC20

            log.info("MoC Bucket ({0}) using address: {1}".format(ca['name'], moc_bucket_address))

            moc_bucket = contract_interface(
                self.connection_helper.connection_manager,
                contract_address=moc_bucket_address)

            self.contracts_loaded['Moc'].append(moc_bucket)
            self.moc_buckets_addresses.append(moc_bucket_address)

            if ca['type']  == 'rc20':
                ca_token_address = moc_bucket.ac_token()
                ca_token = ERC20Token(
                    self.connection_helper.connection_manager,
                    contract_address=ca_token_address)
                self.contracts_loaded["CA_TOKEN"].append(ca_token)

            # Get TP Price provider... in multi-collateral we have the assumption that all collateral
            # have the same TPs, this why only watch the first collateral only

            price_providers = []
            for tp_i, tp in enumerate(self.config['pegged']):
                try:
                    tp_address = self.contracts_loaded["Moc"][ca_index].tp_tokens(tp_i)
                except Web3RPCError:
                    continue
                if not tp_address:
                    break
                tp_index = self.contracts_loaded["Moc"][ca_index].pegged_token_index(tp_address)
                # result: tp_index = [index, enabled]
                if not tp_index:
                    break
                tp_item = self.contracts_loaded["Moc"][ca_index].peg_container(tp_index[0])
                # result: tp_item = [index, price provider]
                price_providers.append(tp_item[1])

            # load TP price providers
            self.contracts_loaded["PriceProviders"] = []
            for pp_address_index, pp_address in enumerate(price_providers):
                log.info("Price Provider TP ({0}) using address: {1}".format(
                    self.config['pegged'][pp_address_index]['name'], pp_address))
                pp = PriceProvider(
                    self.connection_helper.connection_manager,
                    contract_address=pp_address)
                self.contracts_loaded["PriceProviders"].append(pp)

        # MoCMedianizer
        if 'oracle_poke' in self.config['tasks']:
            self.contracts_loaded["MoCMedianizer"] = MoCMedianizer(
                self.connection_helper.connection_manager,
                contract_address=self.config['addresses']['MoCMedianizer'])
            self.contracts_addresses['MoCMedianizer'] = self.contracts_loaded["MoCMedianizer"].address().lower()

        # Commission splitters
        if 'commission_splitters' in self.config['tasks']:
            count = 0
            for setting_commission in self.config['tasks']['commission_splitters']:
                self.contracts_loaded["CommissionSplitter_{0}".format(count)] = CommissionSplitter(
                    self.connection_helper.connection_manager,
                    contract_address=setting_commission['address'])
                self.contracts_addresses["CommissionSplitter_{0}".format(count)] = self.contracts_loaded["CommissionSplitter_{0}".format(count)].address().lower()

                # Token
                self.contracts_loaded["CommissionSplitter_Token_{0}".format(count)] = ERC20Token(
                    self.connection_helper.connection_manager,
                    contract_address=setting_commission['ac_token'])
                self.contracts_addresses["CommissionSplitter_Token_{0}".format(count)] = self.contracts_loaded["CommissionSplitter_Token_{0}".format(count)].address().lower()

                # Fee Token
                if setting_commission['fee_token']:
                    self.contracts_loaded["CommissionSplitter_FeeToken_{0}".format(count)] = ERC20Token(
                        self.connection_helper.connection_manager,
                        contract_address=setting_commission['fee_token'])
                    self.contracts_addresses["CommissionSplitter_FeeToken_{0}".format(count)] = self.contracts_loaded[
                        "CommissionSplitter_FeeToken_{0}".format(count)].address().lower()

                count += 1

    def schedule_tasks(self):

        log.info("Starting adding tasks...")

        # set max workers
        self.max_workers = 1

        for count, moc_address in enumerate(self.moc_buckets_addresses):
            # run_settlement
            if 'execute_settlement' in self.config['tasks']:
                log.info("Jobs add: 1. Execute Settlement. Bucket: (%s) %s" % (
                    self.config['collateral'][count]['name'], moc_address)
                         )
                interval = self.config['tasks']['execute_settlement']['interval']
                self.add_task(self.execute_settlement,
                              args=[count],
                              wait=interval,
                              timeout=180,
                              task_name='1. Execute Settlement. Bucket: (%s) %s' % (
                                  self.config['collateral'][count]['name'], moc_address)
                              )

            # calculate EMA
            if 'calculate_ema' in self.config['tasks']:
                log.info("Jobs add: 2. Calculate EMA. Bucket: (%s) %s" % (
                    self.config['collateral'][count]['name'], moc_address)
                         )
                interval = self.config['tasks']['calculate_ema']['interval']
                self.add_task(self.calculate_ema,
                              args=[count],
                              wait=interval,
                              timeout=180,
                              task_name='2. Calculate EMA. Bucket: (%s) %s' % (
                                  self.config['collateral'][count]['name'], moc_address)
                              )

            # tc_holders_interest_payment
            if 'tc_holders_interest_payment' in self.config['tasks']:
                log.info("Jobs add: 3. Run TC Holders Interest Payment. Bucket: (%s) %s" % (
                    self.config['collateral'][count]['name'], moc_address)
                         )
                interval = self.config['tasks']['tc_holders_interest_payment']['interval']
                self.add_task(self.tc_holders_interest_payment,
                              args=[count],
                              wait=interval,
                              timeout=180,
                              task_name='3. Run TC Holders Interest Payment. Bucket: (%s) %s' % (
                                  self.config['collateral'][count]['name'], moc_address)
                              )

        # Oracle Poke
        if 'oracle_poke' in self.config['tasks']:
            log.info("Jobs add: 4. Oracle Compute")
            interval = self.config['tasks']['oracle_poke']['interval']
            self.add_task(self.oracle_poke,
                          args=[],
                          wait=interval,
                          timeout=180,
                          task_name='4. Oracle Compute')

        # Commission splitters
        if 'commission_splitters' in self.config['tasks']:
            count = 0
            for setting_commission in self.config['tasks']['commission_splitters']:
                log.info("Jobs add: 5. Commission Splitter: {0}".format(setting_commission['address']))
                interval = setting_commission['interval']
                self.add_task(self.commission_splitter,
                              args=[count],
                              wait=interval,
                              timeout=180,
                              task_name="5. Commission Splitter: {0}".format(setting_commission['address']))
                count += 1

        # Refresh AC Balance (after commission spliter execution)
        if 'refresh_ac_balance' in self.config['tasks']:
            count = 0
            count_token = 0
            for collateral in self.config['collateral']:
                if collateral['type'] == 'rc20':
                    log.info("Jobs add: 6. Refresh AC Balance. Index: %s" % count)
                    interval = self.config['tasks']['refresh_ac_balance']['interval']
                    self.add_task(self.refresh_ac_balance,
                                  args=[count, count_token],
                                  wait=interval,
                                  timeout=180,
                                  task_name='6. Refresh AC Balance. Index: %s' % count)
                    count_token += 1
                count += 1

        # Set max workers
        self.max_tasks = len(self.tasks)
