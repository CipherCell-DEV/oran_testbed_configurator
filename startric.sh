#!/bin/bash
docker compose -f ./repositories/docker-compose.yml  up dbaas rtmgr_sim submgr e2term appmgr e2mgr python_xapp_runner
