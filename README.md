# Chameleon Blazar Tempest Plugin

This is a rewrite / proof-of-concept of the upstream blazar-tempest-plugin, found at https://github.com/openstack/blazar-tempest-plugin

The reason for the rewrite is primarily to make the blazar service client reusable in other test plugins, and secondarily to clean up the existing tests
Ultimately this should be refactored into a fork of the upstream plugin, but the rewrite was done to avoid legacy complications
