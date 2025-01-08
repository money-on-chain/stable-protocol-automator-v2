import decimal
from web3 import Web3
import datetime

from .contracts import Multicall2, Moc, MoCMedianizer, CommissionSplitter

from .base.main import ConnectionHelperBase
from .base.token import ERC20Token
from .tasks_manager import PendingTransactionsTasksManager, on_pending_transactions
from .logger import log
from .utils import aws_put_metric_heart_beat


__VERSION__ = '1.0.9'


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

    @on_pending_transactions
    def calculate_ema(self, task=None, global_manager=None, task_result=None):

        if self.contracts_loaded["Moc"].sc.functions.shouldCalculateEma().call():

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["Moc"].update_emas(
                    gas_limit=self.config['tasks']['calculate_ema']['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = self.config['tasks']['calculate_ema']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def execute_settlement(self, task=None, global_manager=None, task_result=None):

        # Get if block to settlement > 0 to continue
        get_bts = self.contracts_loaded["Moc"].sc.functions.getBts().call()
        if get_bts <= 0:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["Moc"].execute_settlement(
                    gas_limit=self.config['tasks']['execute_settlement']['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = self.config['tasks']['execute_settlement']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def tc_holders_interest_payment(self, task=None, global_manager=None, task_result=None):

        # Get if block to settlement > 0 to continue
        next_payment_block = self.contracts_loaded["Moc"].sc.functions.nextTCInterestPayment().call()
        current_block = self.connection_helper.connection_manager.block_number
        if current_block > next_payment_block:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["Moc"].tc_holders_interest_payment(
                    gas_limit=self.config['tasks']['tc_holders_interest_payment']['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = self.config['tasks']['tc_holders_interest_payment']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

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

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["MoCMedianizer"].poke(
                    gas_limit=self.config['tasks']['oracle_poke']['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = self.config['tasks']['oracle_poke']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

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

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["CommissionSplitter_{0}".format(index)].split(
                    gas_limit=commission_setting['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = commission_setting['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result

    @on_pending_transactions
    def refresh_ac_balance(self, task=None, global_manager=None, task_result=None):

        ac_balance = self.contracts_loaded["CA_TOKEN"].balance_of(self.contracts_loaded["Moc"].contract_address)
        ac_balance_collateral_bag = Web3.from_wei(self.contracts_loaded["Moc"].ac_balance_collateral_bag(), 'ether')
        locked_in_pending = Web3.from_wei(self.contracts_loaded["Moc"].locked_in_pending(), 'ether')

        if ac_balance > ac_balance_collateral_bag + locked_in_pending:

            # return if there are pending transactions
            if task_result.get('pending_transactions', None):
                return task_result

            web3 = self.connection_helper.connection_manager.web3

            nonce = web3.eth.get_transaction_count(
                self.connection_helper.connection_manager.accounts[0].address, "pending")

            # get gas price from node
            node_gas_price = decimal.Decimal(Web3.from_wei(web3.eth.gas_price, 'ether'))

            try:
                tx_hash = self.contracts_loaded["Moc"].refresh_ac_balance(
                    gas_limit=self.config['tasks']['refresh_ac_balance']['gas_limit'],
                    max_fee_per_gas=self.config['max_fee_per_gas'],
                    max_priority_fee_per_gas=self.config['max_priority_fee_per_gas'],
                    nonce=nonce
                )
            except ValueError as err:
                log.error("Task :: {0} :: Error sending transaction! \n {1}".format(task.task_name, err))
                return task_result

            if tx_hash:
                new_tx = dict()
                new_tx['hash'] = tx_hash
                new_tx['timestamp'] = datetime.datetime.now()
                new_tx['gas_price'] = node_gas_price
                new_tx['nonce'] = nonce
                new_tx['timeout'] = self.config['tasks']['refresh_ac_balance']['wait_timeout']
                task_result['pending_transactions'].append(new_tx)

                log.info("Task :: {0} :: Sending TX :: Hash: [{1}] Nonce: [{2}] Gas Price: [{3}]".format(
                    task.task_name, Web3.to_hex(new_tx['hash']), new_tx['nonce'], int(node_gas_price * 10 ** 18)))

        else:
            log.info("Task :: {0} :: No!".format(task.task_name))

        return task_result


class AutomatorTasks(Automator):

    def __init__(self, config):

        self.config = config
        self.connection_helper = ConnectionHelperBase(config)

        self.contracts_loaded = dict()
        self.contracts_addresses = dict()

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

        # Moc
        self.contracts_loaded["Moc"] = Moc(
            self.connection_helper.connection_manager,
            contract_address=self.config['addresses']['Moc'])
        self.contracts_addresses['Moc'] = self.contracts_loaded["Moc"].address().lower()

        if self.config['collateral'] == 'rc20':
            ac_token = self.contracts_loaded["Moc"].ac_token()
            self.contracts_loaded["CA_TOKEN"] = ERC20Token(
                self.connection_helper.connection_manager,
                contract_address=ac_token)

        # MoCMedianizer
        if 'oracle_poke' in self.config['tasks']:
            self.contracts_loaded["MoCMedianizer"] = MoCMedianizer(
                self.connection_helper.connection_manager,
                contract_address=self.config['addresses']['MoCMedianizer'])
            self.contracts_addresses['MoCMedianizer'] = self.contracts_loaded["MoCMedianizer"].address().lower()

        # Multicall
        self.contracts_loaded["Multicall2"] = Multicall2(
            self.connection_helper.connection_manager,
            contract_address=self.config['addresses']['Multicall2'])

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

        # run_settlement
        if 'execute_settlement' in self.config['tasks']:
            log.info("Jobs add: 1. Execute Settlement")
            interval = self.config['tasks']['execute_settlement']['interval']
            self.add_task(self.execute_settlement,
                          args=[],
                          wait=interval,
                          timeout=180,
                          task_name='1. Execute Settlement')

        # calculate EMA
        if 'calculate_ema' in self.config['tasks']:
            log.info("Jobs add: 2. Calculate EMA")
            interval = self.config['tasks']['calculate_ema']['interval']
            self.add_task(self.calculate_ema,
                          args=[],
                          wait=interval,
                          timeout=180,
                          task_name='2. Calculate EMA')

        # tc_holders_interest_payment
        if 'tc_holders_interest_payment' in self.config['tasks']:
            log.info("Jobs add: 3. Run TC Holders Interest Payment")
            interval = self.config['tasks']['tc_holders_interest_payment']['interval']
            self.add_task(self.tc_holders_interest_payment,
                          args=[],
                          wait=interval,
                          timeout=180,
                          task_name='3. Run TC Holders Interest Payment')

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
        if 'refresh_ac_balance' in self.config['tasks'] and self.config['collateral'] == 'rc20':
            log.info("Jobs add: 6. Refresh AC Balance")
            interval = self.config['tasks']['refresh_ac_balance']['interval']
            self.add_task(self.refresh_ac_balance,
                          args=[],
                          wait=interval,
                          timeout=180,
                          task_name='6. Refresh AC Balance')

        # Set max workers
        self.max_tasks = len(self.tasks)
