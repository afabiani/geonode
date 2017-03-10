#!/bin/bash

set -x 
set -h

CURRENT=$(dirname $0)
DEPLOY_BASE='../../../geonode/contrib/risks/static/'
ASSETS_DIR="${DEPLOY_BASE}assets"
DIST_DIR="${DEPLOY_BASE}js"

pushd ${CURRENT}
mkdir -p tmp-dmc/
cd tmp-dmc

if [ -f .git/config ] ;then
    git pull
else
    git clone --recursive https://github.com/geosolutions-it/disastermanagement-client.git .
fi;
npm install
npm run compile

mkdir -p ${ASSETS_DIR}
mkdir -p ${DIST_DIR}

cp -vvr assets/* ${ASSETS_DIR}
cp -vvr dist/* ${DIST_DIR}

echo "client code updated. Temp workdir is in" 
echo $(pwd)
echo "you can remove this directory if you want to make clean update"
echo ""
echo "if needed (and if not you customized somehow), copy the file"
echo $(pwd)"/localConfig.json"
echo "into ${DIST_DIR}"
