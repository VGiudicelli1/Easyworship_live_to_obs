###################################################################################################
##  used by eventlet. Need to be imported manually for pyinstaller to add it                     ##
###################################################################################################
import eventlet.patcher, eventlet.hubs
import eventlet.hubs.epolls, eventlet.hubs.kqueue, eventlet.hubs.selects
import dns, dns.rdtypes, dns.rdtypes.ANY, dns.rdtypes.IN, dns.rdtypes.CH
import dns.rdtypes.dnskeybase, dns.asyncbackend, dns.dnssec, dns.e164
import dns.namedict, dns.tsigkeyring, dns.versioned
import socketserver
import http.server as _http_server
from engineio.async_drivers import eventlet as _engineio_async_drivers_eventlet

if __name__ == "__main__":
    print(
        dns,
        socketserver,
        _http_server,
        _engineio_async_drivers_eventlet,
        eventlet.patcher,
    )
