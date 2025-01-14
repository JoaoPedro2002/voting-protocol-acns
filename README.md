# voting-protocol-acns

Implementation for the ACNS 2025 paper ""

## Execute all players

```bash
docker-compose up
```

This will start the following containers:

- `db`: A PostgreSQL database in port 5432
- `rabbitmq`: A RabbitMQ broker in port 5672 and 15672
- `helios`: The Helios server in port 8000
- `helios_worker`: A Celery worker for Helios
- `return_code_server`: The return code server in port 8001
- `shuffle_server`: The shuffle server in port 8002
- `auditor`: The auditor in port 8003
- `phone`: A phone in port 8004
- `voter`: A voter in port 8005

## Run an election

### Users

We use the default ldap users: riemann, gauss, euler, euclid, einstein, newton, galieleo, tesla

All users have the password `password`

### Create a new election

After starting the containers, you can create a new election by entering the Helios server at `http://localhost:8000`, 
logging in with any of the users above with the ldap option and selecting `create election`.

In the form, make sure in the Protocol section you select `Quantum-Safe` and set:
- the Shuffle Server URL to `http://localhost:8002`, 
- the Return Code Server URL to `http://localhost:8001` 
- and the Auditor URLs to `http://localhost:8003`.

To be able to vote in the election, set the `Voting starts at` to a date in the past.

After creating the election, you can add questions to it in the `questions (0)` tab 
and, in the `voters & ballots` tab, select the option `anyone can vote` and click on `update`.

After that, freeze the election and you can start voting.

### Voting

You can vote via the api or the desktop.

#### Desktop

To execute the desktop, run the following command:

```bash
make desktop
```

This will start a desktop application that allows you to vote in the election.

First, you need to enter the Helios server URL (http://localhost:8000) and log in with any of the users above.

After that, you can select to register in the election.

To register, you need:
- the election uuid: you can get it from the URL of the election in the Helios server election page
- the voter phone (http://localhost:8004)

After registering, you can vote in the election.

Select the answers for the questions and submit the vote.

To see the progress of the election, you can check the logs of the containers. 
Additionally, you can check the ballot tracking in the Helios server in the url 
`http://localhost:8000/helios/elections/<election-uuid>/voters/list`.

#### API

First define the election uuid:

```bash
export ELECTION_UUID=<election-uuid>
````

By default in this script all the users are registered and vote in the election. 
if you want to select only some users, you can define the users in the following variable:

```bash
export ELECTION_USERS=<user1>,<user2>,...
```

Then, you can vote with the following command:

```bash
make vote
``` 

Each voter selects a random answer for each question and submits the vote.

### Counting

The votes can be counted going to the Helios server and selecting the option `compute encrypted tally` in the election page.

Reload the page and verify the results. After that, the results will be decrypted and the election will be closed.

## Lib and Benchmarks

First compile the shared library and add it to the library path, if you voted via desktop the library is already compiled.

```bash
make lib
```

Then you can run the benchmarks with the following command:

```bash
make benchmark
```











