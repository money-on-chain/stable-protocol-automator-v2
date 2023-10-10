# Stable Protocol Automator v2

This is a backend executor jobs. Periodic tasks that runs different jobs, 
that call the contracts and asks if they are ready to execute it. This jobs 
run async of the app, and call directly to the contract through node. 

### Currents tasks

 1. Contract calculate EMA
 2. Contract run settlement
 3. Oracle Compute: Check expiration of price in Oracle.
 
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
docker build -t automator -f Dockerfile --build-arg CONFIG=./enviroments/flipago-testnet/config.json .
```

Run, replace ACCOUNT_PK_SECRET  with your private key owner of the account

```
docker run -d \
--name automator_1 \
--env ACCOUNT_PK_SECRET=asdfasdfasdf \
automator
```
