# Stable Protocol Automator v2

## Warning: This is only for version 2 of the main contracts.

This is a backend executor jobs. Periodic tasks that runs different jobs, 
that call the contracts and asks if they are ready to execute it. This jobs 
run async of the app, and call directly to the contract through node. 

### Currents tasks

 1. Contract calculate EMA if it's the time
 2. Contract run settlement if it's the time
 3. Pay TC Holders Interest if it's the time
 4. Oracle Compute: Check expiration of price in Oracle.
 5. Run Commission Splitter if need it
 6. Refresh AC Balance
 
### Usage

**Requirement and installation**
 
*  We need Python 3.10+

Install libraries

`pip install -r requirements.txt`

**Usage**

Select settings from environments/ and copy to ./config.json 

**Run**

`export ACCOUNT_PK_SECRET=(Your PK)`

`python ./app_run_automator.py `

#### Custom node instead using of public node

If you want to use your custom private node pass as environment settings, before running price feeder:

`export APP_CONNECTION_URI=https://public-node.rsk.co`


**Usage Docker**

Build, change path to correct environment

```
docker build -t automator_v2 -f Dockerfile --build-arg CONFIG=./enviroments/production/roc-mainnet/config.json .
```

Run, replace ACCOUNT_PK_SECRET  with your private key owner of the account

```
docker run -d \
--name automator_1 \
--env ACCOUNT_PK_SECRET=asdfasdfasdf \
automator_v2
```

### Contracts


**Stable protocol core v2**

*[https://github.com/money-on-chain/stable-protocol-core-v2](https://github.com/money-on-chain/stable-protocol-core-v2)*

**RIF on Chain implementation v2**

*[https://github.com/money-on-chain/stable-protocol-roc-v2](https://github.com/money-on-chain/stable-protocol-roc-v2)*

**Flipmoney implementation v2**

*[https://github.com/money-on-chain/stable-protocol-roc-v2](https://github.com/money-on-chain/stable-protocol-roc-v2)*

**Money on Chain implementation v2**

*[https://github.com/money-on-chain/stable-protocol-moc-v2](https://github.com/money-on-chain/stable-protocol-moc-v2)*
