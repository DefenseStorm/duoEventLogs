#!/usr/bin/env python

import sys,os,getopt
sys.path.insert(0, 'duo_client_python')
import duo_client

import traceback
import os
from datetime import datetime
import calendar

sys.path.insert(0, 'ds-integration')
from DefenseStorm import DefenseStorm

class integration(object):

    def get_logs(self):
        '''
        Connects to the DuoSecurity API and grabs the admin
        and auth logs, which are then parsed and passed to
        log)to_cef().
        '''
        admin_api = duo_client.Admin(
            ikey=self.ds.config_get('api', 'INTEGRATION_KEY'),
            skey=self.ds.config_get('api', 'SECRET_KEY'),
            host=self.ds.config_get('api', 'API_HOST'))

        # Check to see if DELTA is 0. If so, retrieve all logs.

        date = datetime.utcnow()
        utc_date = calendar.timegm(date.utctimetuple())
        mintime = utc_date - int(self.ds.config_get('api', 'DELTA'))

        if mintime == utc_date:
            self.ds.log('INFO', "Collecting all logs (to maxminum for API)")
            admin_log = admin_api.get_administrator_log()
            auth_log = admin_api.get_authentication_log()
        else:
            self.ds.log('INFO', "Collecting logs for last " + self.ds.config_get('api', 'DELTA') + ' seconds')
            admin_log = admin_api.get_administrator_log(mintime=mintime)
            auth_log = admin_api.get_authentication_log(mintime=mintime)

        self.ds.log('INFO', "Administrator Log Count: %d" %len(admin_log))
        self.ds.log('INFO', "Auth Log Count: %d" %len(auth_log))

        for entry in admin_log:
            # timestamp is converted to milliseconds for CEF
            # repr is used to keep '\\' in the domain\username
            extension = {
                'duser': repr(entry['username']).lstrip("u").strip("'"),
                'rt': str(entry['timestamp'] * 1000),
                'description': str(entry.get('description')),
                'dhost': entry['host'],
            }

            self.ds.writeCEFEvent(type=entry['eventtype'], action=entry['eventtype'], dataDict=extension)

        for entry in auth_log:
            # timestamp is converted to milliseconds for CEF
            # repr is used to keep '\\' in the domain\username
            extension = {
                'rt': str(entry['timestamp'] * 1000),
                'src': entry['ip'],
                'dhost': entry['host'],
                'duser': repr(entry['username']).lstrip("u").strip("'"),
                'outcome': entry['result'],
                'cs1Label': 'new_enrollment',
                'cs1': str(entry['new_enrollment']),
                'cs2Label': 'factor',
                'cs2': entry['factor'],
                'cs3Label': 'integration',
                'cs3': entry['integration'],
            }

            self.ds.writeCEFEvent(type=entry['eventtype'], action=entry['eventtype'], dataDict=extension)


    def run(self):
        self.get_logs()
    
    def usage(self):
        print
        print os.path.basename(__file__)
        print
        print '  No Options: Run a normal cycle'
        print
        print '  -t    Testing mode.  Do all the work but do not send events to GRID via '
        print '        syslog Local7.  Instead write the events to file \'output.TIMESTAMP\''
        print '        in the current directory'
        print
        print '  -l    Log to stdout instead of syslog Local6'
        print
    
    def __init__(self, argv):

        self.testing = False
        self.send_syslog = True
        self.ds = None
    
        try:
            opts, args = getopt.getopt(argv,"htnld:",["datedir="])
        except getopt.GetoptError:
            self.usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                self.usage()
                sys.exit()
            elif opt in ("-t"):
                self.testing = True
            elif opt in ("-l"):
                self.send_syslog = False
    
        try:
            self.ds = DefenseStorm('duoEventLogs', testing=self.testing, send_syslog = self.send_syslog)
        except Exception ,e:
            traceback.print_exc()
            try:
                self.ds.log('ERROR', 'ERROR: ' + str(e))
            except:
                pass


if __name__ == "__main__":
    i = integration(sys.argv[1:]) 
    i.run()
