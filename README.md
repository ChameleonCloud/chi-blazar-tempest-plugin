# Chameleon Blazar Tempest Plugin

This is a rewrite / proof-of-concept of the upstream blazar-tempest-plugin, found at https://github.com/openstack/blazar-tempest-plugin

The reason for the rewrite is primarily to make the blazar service client reusable in other test plugins, and secondarily to clean up the existing tests
Ultimately this should be refactored into a fork of the upstream plugin, but the rewrite was done to avoid legacy complications



# Test Cases



## API

* Lease
  * Show
  * List
  * Create
  * Update
  * Delete
* Reservable Host
  * Show
  * List
  * Create
  * Update
  * Delete
* Allocation
  * Show
  * List
  * Create
  * Update
  * Delete

* Extend lease within "2d" window
* Extend lese outside "2d" window (negative)
* Create lease under "7d" window
* Create lease over "7d" window (negative)
* Launch node on expired lease (negative)
* Launch node on lease from other project (negative)
* launch 2 nodes on lease for 1 node (negative)
* launch node with baremetal flavor without a lease (negative)
* launch node with baremetal flavor with non-existing lease (negative)
  
## Scenario

### requires baremetal node
* Reserve a Node: TestReservableServerBasicOps.test_server_basic_ops

### can use VM for speedup
* Reserve Vlan + Verify
* Reserve Storage VLAN + verify
* Resrve stitchable vlan + verify
* reserve floating IP + verify
