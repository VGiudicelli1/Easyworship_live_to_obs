import socket
import threading
import dns.resolver
import collections
import time
import json
import struct
import re
import storage
import logger

class API:
    socket: "socket.socket"
    tx_thread: threading.Thread
    rx_thread: threading.Thread
    description: str
    connected: bool
    tx_queue: collections.deque

    resolver: dns.resolver.Resolver
    host: str
    port: int

    logger: "logger.Logger"

    def __init__(
            self: "API", 
            description: str,
            host:str, port:int=5353, 
            logger:'logger.Logger' = logger.LoggerPrint()
        ):
        self.description = description
        self.connected = False
        self.host = host
        self.port = port

        self.resolver = dns.resolver.Resolver(configure=False)
        self.resolver.nameservers = [addrinfo[4][0] for addrinfo in socket.getaddrinfo(host, 5353, proto=socket.IPPROTO_UDP)]
        self.resolver.port = port
        self.resolver.timeout = 3

        self.logger = logger

        self.tx_queue = collections.deque()

        self.socket = None
        self.tx_thread = None
        self.rx_thread = None

    def connect(self: "API") -> bool:
        # clean up any existing connection
        self.disconnect()
        
        try:
            # resolve mdns records to determine dynamic EW port (new in EW 7.2.3)
            self.logger.log('Searching for EW on ' + str(self.resolver.nameservers) + '...')
            resolution = self.resolver.resolve('_ezwremote._tcp.local.', rdtype=dns.rdatatype.PTR)
            srv_name = resolution.rrset[0].target
            self.port = resolution.response.find_rrset(dns.message.ADDITIONAL, srv_name, dns.rdataclass.IN, dns.rdatatype.SRV)[0].port
        
            # open new socket
            self.logger.log('Connecting to EW at ' + self.host + ' port ' + str(self.port) + '...')
            self.socket = socket.create_connection((self.host, self.port), 7)
        except (OSError, dns.exception.Timeout, dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            self.socket = None
            self.logger.error('Connecting to EW failed!')
            return False
        else:
            self.logger.log('Connected to EW.')
            self.connected = True
            
            # flush tx message queue
            self.tx_queue.clear()
            
            # start communication threads
            self.tx_thread = threading.Thread(target=self.send, name=self.description+'tx_thread', args=([self.socket]))
            self.tx_thread.start()
            self.rx_thread = threading.Thread(target=self.recv, name=self.description+'rx_thread', args=([self.socket]))
            self.rx_thread.start()

            return True

    def disconnect(self: "API"):
        self.connected = False
        if (self.socket):
            self.logger.log('Closing connection to ' + self.description + '...')
            # close existing socket if applicable
            try:
                self.socket.settimeout(0)
            except OSError:
                pass
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.socket.settimeout(None)
            except OSError:
                pass
            try:
                self.socket.close()
            except OSError:
                pass
        
        # wait for communication threads to die if applicable
        if self.tx_thread:
            if self.tx_thread.is_alive():
                self.logger.log('Waiting for ' + self.description + ' transmit to finish...')
                self.tx_thread.join()
        if self.rx_thread:
            if self.rx_thread.is_alive():
                self.logger.log('Waiting for ' + self.description + ' receive to finish...')
                self.rx_thread.join()

    def send(self: "API"):
        pass

    def recv(self: "API"):
        pass


class EW_API (API):
    client_id: str
    storage: "storage.Storage"
    credit_slide_re: "re.Pattern"
    presentation_filter_re: "re.Pattern"
    presentation_filter: "list[str]"

    def __init__(
            self: "EW_API", 
            host: str = '192.168.1.213', 
            client_id: str = 'a164e834-fc66-4cff-8e47-aa904ee9e62b', 
            logger: logger.Logger = logger.LoggerPrint(), 
            credit_slide: "list[str]" = ['Title', 'Credit', 'Credits'],
            presentation_filter: "list[str]" = []):
        super().__init__("EW", host, logger=logger)
        self.client_id = client_id
        self.storage = storage.Storage()

        if credit_slide:
            self.credit_slide_re = re.compile('(?:\A|\s)(' + '|'.join(credit_slide) + ')(?:\s|\Z)', re.IGNORECASE)
        else:
            self.credit_slide_re = re.compile('\Z.')

        if presentation_filter:
            self.presentation_filter_re = re.compile('(?:\A|\s)(' + '|'.join(presentation_filter) + ')(?:\s|\Z)', re.IGNORECASE)
        else:
            self.presentation_filter_re = None
        self.presentation_filter = presentation_filter

    def connect(self: "EW_API"):
        if super().connect():
            # hello to ew
            self.tx_queue.append(('{"device_type":0,"action":"connect","uid":"' + self.client_id + '","device_name":"ew to obs"}\r\n').encode('utf-8'))
            return True
        return False
    
    def recv(self: "EW_API", ew_socket):
        received_data = b''
        extrabytes_len = 0
        newjson = {}
        newjson_len = -1

        while self.connected:
            try:
                ew_socket.settimeout(None)
                # receive data from socket
                received_data += ew_socket.recv(16384)
            except OSError:
                self.connected = False
            else:
                if len(received_data) < 1:
                    self.connected = False
            finally:
                # find first message delimiter
                newjson_len = received_data.find(b'\r\n')
                while newjson_len != -1:
                    self.logger.recv(received_data[:newjson_len].decode('utf-8').encode('unicode_escape').decode('utf-8'))
                    
                    extrabytes_len = 0
                    try:
                        newjson = json.loads(received_data[:newjson_len].decode('utf-8'))
                    except json.decoder.JSONDecodeError: # message is not valid json
                        newjson = ''
                    else:
                        if newjson.get('action', '') in ['LiveData', 'ScheduleData', 'currentImage', 'slideImage']:
                            # json message says it will have extra bytes following
                            extrabytes_len = int(newjson.get('size', 0))
                    finally:
                        if len(received_data) >= (newjson_len + 2 + extrabytes_len): # message is complete incl extra bytes
                            if newjson != '':
                                # process received message
                                self.procmsg(newjson, received_data[(newjson_len + 2):(newjson_len + 2 + extrabytes_len)])
                            # look in received data for another message
                            received_data = received_data[(newjson_len + 2 + extrabytes_len):]
                            newjson_len = received_data.find(b'\r\n')
                        else:
                            # don't have full message with all extra bytes, need to receive more data
                            newjson_len = -1

    def send(self: "EW_API", ew_socket):
        sentbytestimestamp = time.time()
        
        while self.connected:
            outboundbytes = b''
            try:
                while True:
                    # retrieve queue until it's emptied
                    outboundbytes += self.tx_queue.popleft()
            except IndexError:
                # queue is empty
                if len(outboundbytes) < 1:
                    # no messages retrieved from queue
                    if (time.time() - sentbytestimestamp) > 3:
                        # more than 3 seconds since last transmission, so transmit keepalive
                        outboundbytes = ('{"action":"heartbeat","requestrev":' + str(self.storage.requestrev) + '}\r\n').encode('utf-8')
                    else:
                        # wait before checking the queue again
                        time.sleep(0.002)
                if len(outboundbytes) > 0:
                    sentbytecount_total = 0
                    while sentbytecount_total < len(outboundbytes):
                        try:
                            ew_socket.settimeout(7)
                            sentbytecount = ew_socket.send(outboundbytes[sentbytecount_total:])
                            ew_socket.settimeout(None)
                        except OSError:
                            self.connected = False
                            outboundbytes = b''
                        else:
                            if sentbytecount < 1:
                                self.connected = False
                                outboundbytes = b''
                            else:
                                sentbytestimestamp = time.time()
                                self.logger.send(outboundbytes[sentbytecount_total:sentbytecount_total + sentbytecount].decode('utf-8').encode('unicode_escape').decode('utf-8'))
                                sentbytecount_total += sentbytecount


    def procmsg(self: "EW_API", jsondata: dict, rawdata: bytes):
        
        if 'requestrev' in jsondata:
            self.storage.requestrev = int(jsondata['requestrev'])

        if 'action' in jsondata:
                        
            if jsondata['action'] == 'status':                
                if 'liverev' in jsondata:
                    self.storage.liverev_pending = int(jsondata['liverev'])
                if 'imagehash' in jsondata:
                    self.storage.imagehash_pending = jsondata['imagehash']
                    self.storage.slide_rowid_pending = int(jsondata.get('slide_rowid', -1))
                if True in [bool(jsondata.get('logo', False)), bool(jsondata.get('black', False)), bool(jsondata.get('clear', False))]:
                    self.storage.contentvisible_pending = False
                else:
                    self.storage.contentvisible_pending = True


            elif jsondata['action'] == 'LiveData':
                
                # clear stored slides
                self.storage.clearSlides()
                
                # unpack first part of raw data
                unknownrawdata0, self.storage.liverev, self.storage.pres_rowid, title_revision, pres_len, unknownrawdata5 = struct.unpack('<lqqqlq', rawdata[:40])
                #print((unknownrawdata0, liverev, pres_rowid, title_revision, pres_len, unknownrawdata5))
                            
                # request title info
                self.tx_queue.append(('{"slide_rowid":0,"revision":' + str(title_revision) + 
                                      ',"action":"getSlideInfo","requestrev":' + str(self.storage.requestrev) + 
                                      ',"rectype":1,"pres_rowid":' + str(self.storage.pres_rowid) + 
                                      '}\r\n').encode('utf-8'))
                
                # store preliminary info of each slide
                for i in range(pres_len):
                    rowid, revision = struct.unpack('<qq', rawdata[(40 + (16 * i)):(56 + (16 * i))])
                    self.storage.setSlide(storage.Slide(
                        id=i,
                        rowid=rowid,
                        revision=revision
                    ))
                                                

            elif jsondata['action'] == 'slideInfo' and 'slide_rowid' in jsondata:
                
                if int(jsondata['slide_rowid']) == 0: # slide 0 info is for the song title (not for an actual slide)
                    if 'title' in jsondata:
                        title = jsondata['title']
                        
                if self.storage.hasSlide(int(jsondata['slide_rowid'])): # info is for a valid slide
                    
                    if self.credit_slide_re.search(jsondata.get('title', '')): # slide is a special slide of custom song credits
                        self.storage.credit = jsondata.get('content', '')
                        # store blank lyrics for this slide
                        self.storage.getSlide(int(jsondata['slide_rowid'])).reciveInfo('', '')
                        
                    else: # info is for regular slide
                        self.storage.getSlide(int(jsondata['slide_rowid'])).reciveInfo(
                            jsondata['content'] if 'content' in jsondata else '', 
                            jsondata['title'] if 'title' in jsondata else ''
                        )
                    
                    if not self.presentation_filter_re: # presentation filtering is not enabled
                        self.storage.presentation_filtered = False
                    else:
                        if self.presentation_filter_re.search(jsondata.get('title', '')): # slide title matches filter
                            self.storage.presentation_filtered = False
        
        
        #global content_sent, contentvisible, contentvisible_pending, credit, credit_sent, 
        #global imagehash, imagehash_pending, liverev, liverev_pending, pres_rowid, 
        #global presentation_filtered, requestrev, slide_rowid_pending, slides, title
        

        if self.storage.contentvisible_pending: # content should be visible
            
            if self.storage.imagehash_pending != self.storage.imagehash: # outdated content is currently output
                
                if self.storage.liverev_pending != self.storage.liverev: # outdated slides are currently loaded
                    # invalidate queued outbound requests
                    self.tx_queue.clear()
                    # clear stored slides
                    self.storage.clearSlides()

                    # request data about new song
                    self.tx_queue.append(('{"action":"GetLiveData","requestrev":' + str(self.storage.requestrev) + '}\r\n').encode('utf-8'))
                
                else:
                    # make sure all slides are loaded
                    waiting_for_slideinfo = False
                    for slide in self.storage.getAllSlides():
                        if not slide.infoRequested:
                            slide.requestInfo()
                            self.tx_queue.append(('{"slide_rowid":' + str(slide.rowid) + 
                                                  ',"revision":' + str(slide.revision) + 
                                                  ',"action":"getSlideInfo","requestrev":' + str(self.storage.requestrev) + 
                                                  ',"rectype":1,"pres_rowid":' + str(self.storage.pres_rowid) + 
                                                  '}\r\n').encode('utf-8'))
                        if not slide.infoRecived:
                            waiting_for_slideinfo = True
                        
                    currentSlide = self.storage.getCurrentSlide()
                    if not waiting_for_slideinfo and currentSlide:
                        if self.storage.presentation_filtered:
                            self.logger.log('Presentation ignored by filter ("' + '" or "'.join(self.presentation_filter) + '").')
                            self.storage.contentvisible_pending = False
                        else:
                            if currentSlide.content: # we have the content of the new slide
                                self.logger.event(str(currentSlide))
                                self.storage.imagehash = self.storage.imagehash_pending
                                
            if self.storage.imagehash_pending == self.storage.imagehash: # correct content is currently output
                if not self.storage.contentvisible: # content should be visible but is currently hidden
                    self.logger.event('set content visible')
                    self.storage.contentvisible = True
                    
        if (not self.storage.contentvisible_pending) and self.storage.contentvisible: # content should be hidden but is currently visible
            # send hide commands to vm
            self.logger.event('set content unvisible')
            self.storage.contentvisible = False

if __name__ == '__main__':
    ew = EW_API()
    try:
        while True:
            ew.connect()
            time.sleep(3)
    except KeyboardInterrupt:
        print('\33[91mEW2VM TERMINATING...\033[0m')
        
    finally:
        ew.disconnect()

    print('\33[91mEW2VM FINISHED.\033[0m')

