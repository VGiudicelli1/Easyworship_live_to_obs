import dns.resolver
import socket

'''''
resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = [addrinfo[4][0] for addrinfo in socket.getaddrinfo('*.*.*.*', 5353, proto=socket.IPPROTO_UDP)]
resolver.port = 5353
resolver.timeout = 3


resolution = resolver.resolve('_ezwremote._tcp.local.', rdtype=dns.rdatatype.PTR)
srv_name = resolution.rrset[0].target
port = resolution.response.find_rrset(dns.message.ADDITIONAL, srv_name, dns.rdataclass.IN, dns.rdatatype.SRV)[0].port
        '''
#print([addrinfo[4][0] for addrinfo in socket.getaddrinfo('192.168.0.*', 5353, proto=socket.IPPROTO_UDP)])



print ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1])