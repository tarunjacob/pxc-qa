Sysbench Loadtest QA script
---------------------------
This suite will help us to test the workload in Percona XtraDB Cluster. To enable encryption options you should use the argument --encryption-run with pxc qa framework.

Currently we are using following sysbench testsuite for workload test.
* sysbench_customized_dataload_test.py
  * This testsuite will help us to test PXC with different table creation options
* sysbench_load_test.py
  * This testsuite will help us to test PXC with huge tables. 
* sysbench_oltp_test.py
  * This testsuite will help us to test PXC with OLTP transactions.
* sysbench_random_load_test.py
  * This testsuite will help us to test PXC with random load.
* sysbench_read_only_test.py
  * This testsuite will help us to test PXC with read only transactions.
* sysbench_wsrep_provider_option_random_test.py
  * This testsuite will help us to test PXC with different wsrep provider options

PS : We can customize the sysbench data size through [config.ini](../config.ini)
