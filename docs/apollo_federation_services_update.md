# Apollo Federation SERVICES config update
# This file documents the change from host.docker.internal to the correct Docker network service name for the "evolution" service.
#
# The Apollo container should use the internal Docker network to reach the FastAPI service, not host.docker.internal.
#
# Change:
#   {"name": "evolution", "url": "http://host.docker.internal:8000/gql"}
# To:
#   {"name": "evolution", "url": "http://frontend:8000/gql"}
#
# This matches the service name in docker-compose and the port exposed by the frontend container.
#
# After this change, Apollo will be able to reach the FastAPI service via the Docker network.
