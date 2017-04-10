# Test to create, run and destroy a docker image/container with appetite installed

#!/usr/bin/env bash

curr_dir=$PWD
cd "${0%/*}"

# Set WD to Docker file so there are no scope issues
cd ../

function check_rc {
    [ $1 -gt 0 ] && {
      echo < .appetite_stdout
      printf "Error $2\n"
      echo "rc: $1"
      rm -f .appetite_stdout
      exit $3
    }
}

printf "*********** Building Docker image\n"
docker build -t appetite_server . &> .appetite_stdout
check_rc $? "creating docker image" 1

# Create appetite test command to load into docker instance
printf "python /apps/appetite/tests/test.py" > .appetite_test_cmd.txt

printf "*********** Run appetite on docker container\n"
docker run --rm -i appetite_server &> .appetite_stdout < .appetite_test_cmd.txt

check_rc $? "running docker container\ndocker run --rm -ti appetite_server' and run 'appetite_test'" 2
#check_rc $(($output_rc)) "running appetite tests\ndocker run --rm -ti appetite_server' and run 'appetite_test'" 3

printf "*********** Test Passed, Cleaning up\n"
rm -f .appetite_test_cmd.txt .appetite_stdout
docker rmi $(docker images -a | grep appetite_server  | awk '{print $3}' | xargs) &> /dev/null

cd ${curr_dir}
