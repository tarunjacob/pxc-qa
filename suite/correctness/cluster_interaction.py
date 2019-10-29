#!/usr/bin/env python3
import os
import sys
import argparse
import time
import subprocess
cwd = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.normpath(os.path.join(cwd, '../../'))
sys.path.insert(0, parent_dir)
from config import *
from util import pxc_startup
from util import db_connection
from util import sysbench_run
from util import utility
from util import table_checksum
utility_cmd = utility.Utility()
utility_cmd.check_python_version()

# Read argument
parser = argparse.ArgumentParser(prog='PXC replication test', usage='%(prog)s [options]')
parser.add_argument('-e', '--encryption-run', action='store_true',
                    help='This option will enable encryption options')
args = parser.parse_args()
if args.encryption_run is True:
    encryption = 'YES'
else:
    encryption = 'NO'


class ClusterInteraction:
    def __init__(self, basedir, workdir, user, node1_socket, pt_basedir, node):
        self.workdir = workdir
        self.basedir = basedir
        self.user = user
        self.socket = node1_socket
        self.pt_basedir = pt_basedir
        self.node = node

    def run_query(self, query):
        query_status = os.system(query)
        if int(query_status) != 0:
            print("ERROR! Query execution failed: " + query)
            return 1
        return 0

    def start_pxc(self):
        # Start PXC cluster for replication test
        dbconnection_check = db_connection.DbConnection(USER, WORKDIR + '/node1/mysql.sock')
        server_startup = pxc_startup.StartCluster(parent_dir, WORKDIR, BASEDIR, int(self.node))
        result = server_startup.sanity_check()
        utility_cmd.check_testcase(result, "Startup sanity check")
        if encryption == 'YES':
            result = server_startup.create_config('encryption')
            utility_cmd.check_testcase(result, "Configuration file creation")
        else:
            result = server_startup.create_config('none')
            utility_cmd.check_testcase(result, "Configuration file creation")
        result = server_startup.initialize_cluster()
        utility_cmd.check_testcase(result, "Initializing cluster")
        result = server_startup.start_cluster()
        utility_cmd.check_testcase(result, "Cluster startup")
        result = dbconnection_check.connection_check()
        utility_cmd.check_testcase(result, "Database connection")

    def sysbench_run(self, socket, db):
        # Sysbench dataload for consistency test
        sysbench = sysbench_run.SysbenchRun(BASEDIR, WORKDIR,
                                            socket)

        result = sysbench.sanity_check(db)
        utility_cmd.check_testcase(result, "Sysbench run sanity check")
        result = sysbench.sysbench_load(db, SYSBENCH_TABLE_COUNT, SYSBENCH_THREADS, SYSBENCH_NORMAL_TABLE_SIZE)
        utility_cmd.check_testcase(result, "Sysbench data load")
        if encryption == 'YES':
            for i in range(1, SYSBENCH_TABLE_COUNT + 1):
                encrypt_table = BASEDIR + '/bin/mysql --user=root ' \
                    '--socket=' + socket + ' -e "' \
                    ' alter table ' + db + '.sbtest' + str(i) + \
                    " encryption='Y'" \
                    '"; > /dev/null 2>&1'
                os.system(encrypt_table)

        result = sysbench.sysbench_oltp_read_write(db, SYSBENCH_TABLE_COUNT, SYSBENCH_TABLE_COUNT,
                                                   SYSBENCH_NORMAL_TABLE_SIZE, SYSBENCH_RUN_TIME, 'Yes')
        utility_cmd.check_testcase(result, "Initiated sysbench oltp run")

    def startup_check(self, cluster_node):
        """ This method will check the node recovery
            startup status.
        """
        recovery_startup = "bash " + self.workdir + \
                           '/log/startup' + str(cluster_node) + '.sh'
        os.system(recovery_startup)
        ping_query = self.basedir + '/bin/mysqladmin --user=root --socket=' + \
                     WORKDIR + '/node' + cluster_node + '/mysql.sock ping > /dev/null 2>&1'
        for startup_timer in range(120):
            time.sleep(1)
            ping_check = subprocess.call(ping_query, shell=True, stderr=subprocess.DEVNULL)
            ping_status = ("{}".format(ping_check))
            if int(ping_status) == 0:
                utility_cmd.check_testcase(int(ping_status), "Cluster recovery is successful")
                break  # break the loop if mysqld is running

    def flow_control_qa(self):
        """ This method will help us to test cluster
            interaction using following test methods.
            1) Flow control
        """
        self.sysbench_run(self.socket, 'test')
        query = 'pidof sysbench'
        sysbench_pid = os.popen(query).read().rstrip()
        for j in range(1, int(self.node) + 1):
            query = self.basedir + "/bin/mysql --user=root --socket=" + \
                    self.socket + ' -e"set global pxc_strict_mode=DISABLED;' \
                                  '" > /dev/null 2>&1'
            self.run_query(query)
            query = self.basedir + \
                '/bin/mysql ' \
                ' --user=root --socket=' + WORKDIR + '/node1/mysql.sock test' \
                ' -Bse"flush table sbtest1 with read lock;' \
                'select sleep(120);unlock tables"  2>&1 &'
            os.system(query)
            flow_control_status = 'OFF'
            while flow_control_status == 'OFF':
                query = self.basedir + \
                    '/bin/mysql  --user=root --socket=' + WORKDIR + '/node1/mysql.sock' \
                    ' -Bse"show status like ' \
                    "'wsrep_flow_control_status';" + '"' \
                    "| awk '{ print $2 }'  2>&1"
                flow_control_status = os.system(query)
                time.sleep(1)
        kill_sysbench = "kill -9 " + sysbench_pid
        os.system(kill_sysbench)


cluster_interaction = ClusterInteraction(BASEDIR, WORKDIR, USER,
                                         WORKDIR + '/node1/mysql.sock', PT_BASEDIR, NODE)
print('----------------------------------------------')
print('Cluster interaction QA using flow control test')
print('----------------------------------------------')
cluster_interaction.start_pxc()
cluster_interaction.flow_control_qa()
version = utility_cmd.version_check(BASEDIR)
#if int(version) < int("080000"):
#    checksum = table_checksum.TableChecksum(pt_basedir, basedir, workdir, node, node1_socket)
#    checksum.sanity_check()
#    checksum.data_consistency('test')
#else:
result = utility_cmd.check_table_count(BASEDIR, 'test', WORKDIR + '/node1/mysql.sock',
                                       WORKDIR + '/node2/mysql.sock')
utility_cmd.check_testcase(result, "Checksum run for DB: test")
