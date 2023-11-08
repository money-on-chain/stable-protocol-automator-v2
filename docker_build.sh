#!/bin/bash

# exit as soon as an error happen
set -e

usage() { echo "Usage: $0 -e <environment> -c <config file> -i <aws id>" 1>&2; exit 1; }

while getopts ":e:c:i:" o; do
    case "${o}" in
        e)
            e=${OPTARG}
             ((e == "flipago_testnet"  || e=="flipago_mainnet" || e == "roc_testnet" || e == "roc_mainnet")) || usage
            case $e in
                flipago_testnet)
                    ENV=$e
                    ;;
                flipago_mainnet)
                    ENV=$e
                    ;;
                roc_testnet)
                    ENV=$e
                    ;;
                roc_mainnet)
                    ENV=$e
                    ;;
                *)
                    usage
                    ;;
            esac
            ;;
        c)
            c=${OPTARG}
            CONFIG_FILE=$c
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${e}" ] || [ -z "${c}" ]; then
    usage
fi

docker image build -t automator_$ENV -f Dockerfile --build-arg CONFIG=$CONFIG_FILE .

echo "Build done!"