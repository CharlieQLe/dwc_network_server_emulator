"""DWC Network Server Emulator

    Copyright (C) 2014 polaris-
    Copyright (C) 2014 msoucy
    Copyright (C) 2015 Sepalani

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import traceback

from twisted.internet.protocol import Factory
from twisted.internet.endpoints import serverFromString
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
from twisted.internet.error import ReactorAlreadyRunning

import gamespy.gs_database as gs_database
import gamespy.gs_query as gs_query
import other.utils as utils
import dwc_config

logger = dwc_config.get_logger('GameSpyPlayerSearchServer')
address = dwc_config.get_ip_port('GameSpyPlayerSearchServer')


class GameSpyPlayerSearchServer(object):
    def __init__(self):
        pass

    def start(self):
        endpoint_search = serverFromString(
            reactor,
            "tcp:%d:interface=%s" % (address[1], address[0])
        )
        conn_search = endpoint_search.listen(PlayerSearchFactory())

        try:
            if not reactor.running:
                reactor.run(installSignalHandlers=0)
        except ReactorAlreadyRunning:
            pass


class PlayerSearchFactory(Factory):
    def __init__(self):
        logger.log(logging.INFO,
                   "Now listening for player search connections on %s:%d...",
                   address[0], address[1])

    def buildProtocol(self, address):
        return PlayerSearch(address)


class PlayerSearch(LineReceiver):
    def __init__(self, address):
        self.setRawMode()
        self.db = gs_database.GamespyDatabase()

        self.address = address
        self.leftover = ""

    def connectionMade(self):
        pass

    def connectionLost(self, reason):
        pass

    def rawDataReceived(self, data):
        try:
            logger.log(logging.DEBUG, "SEARCH RESPONSE: %s", data)

            data = self.leftover + data
            commands, self.leftover = gs_query.parse_gamespy_message(data)

            for data_parsed in commands:
                print(data_parsed)

                if data_parsed['__cmd__'] == "otherslist":
                    self.perform_otherslist(data_parsed)
                else:
                    logger.log(logging.DEBUG,
                               "Found unknown search command, don't know"
                               " how to handle '%s'.",
                               data_parsed['__cmd__'])
        except:
            logger.log(logging.ERROR,
                       "Unknown exception: %s",
                       traceback.format_exc())

    def perform_otherslist(self, data_parsed):
        """Reference: http://wiki.tockdom.com/wiki/MKWii_Network_Protocol/Server/gpsp.gs.nintendowifi.net"""
        msg_d = [
            ('__cmd__', "otherslist"),
            ('__cmd_val__', ""),
        ]

        if "numopids" in data_parsed and "opids" in data_parsed:
            numopids = int(data_parsed['numopids'])
            opids = data_parsed['opids'].split('|')
            if len(opids) != numopids and int(opids[0]):
                logger.log(logging.ERROR,
                           "Unexpected number of opids, got %d, expected %d.",
                           len(opids), numopids)

            # Return all uniquenicks despite any unexpected/missing opids
            # We can do better than that, I think...
            for opid in opids:
                profile = self.db.get_profile_from_profileid(opid)

                msg_d.append(('o', opid))
                if profile is not None:
                    msg_d.append(('uniquenick', profile['uniquenick']))
                else:
                    msg_d.append(('uniquenick', ''))

        msg_d.append(('oldone', ""))
        msg = gs_query.create_gamespy_message(msg_d)

        logger.log(logging.DEBUG, "SENDING: %s", msg)
        self.transport.write(bytes(msg))


if __name__ == "__main__":
    gsps = GameSpyPlayerSearchServer()
    gsps.start()
