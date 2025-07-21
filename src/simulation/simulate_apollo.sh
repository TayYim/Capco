script_dir=$(dirname "$(realpath "$0")")
config_file="$script_dir/../../env_config.json"

while IFS="=" read -r key value
do
    export $key="$value"
done < <(python3 -c "import json, sys, os; \
    config=json.load(open(os.path.realpath('$config_file'))); \
    env=config.get('env', {}); \
    print('\n'.join([f'{k}={v}' for k, v in env.items()]));")

export PYTHONPATH=${PROJECT_ROOT}:${PYTHONPATH}
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg":${PYTHONPATH}
export PYTHONPATH="${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}

# Process route id passed as argument
if [ -z "\$1" ]
then
    export ROUTES_SUBSET=1
else
    export ROUTES_SUBSET=$1
fi

# Process route name passed as second argument
if [ -z "\$2" ]
then
    export ROUTE_FILE="routes_carlo"
else
    export ROUTE_FILE=$2
fi

export ROUTES=${LEADERBOARD_ROOT}/data/${ROUTE_FILE}.xml
export REPETITIONS=1
export DEBUG_CHALLENGE=0
export TEAM_AGENT=${LEADERBOARD_ROOT}/leaderboard/autoagents/apollo_agent.py
export CHECKPOINT_ENDPOINT=${LEADERBOARD_ROOT}/results.json
export CHALLENGE_TRACK_CODENAME=SENSORS

${LB_PYTHON_PATH} ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--routes=${ROUTES} \
--routes-subset=${ROUTES_SUBSET} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--debug-checkpoint=${DEBUG_CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--record=${RECORD_PATH} \
--resume=${RESUME} \
--passive=True