#!/usr/bin/env python

from zeroconf import ServiceBrowser, Zeroconf
from typing import cast
from threading import Condition
import http.client
import json
import sys
import os
import hashlib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import requests
import threading
import socket


discovered = []
condition = Condition()
data = b""

class MDNSListener:
    def remove_service(self, zeroconf, type, name):
        print("Service removed")
    
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        condition.acquire()
        try:
            discovered.append(info)
            condition.notify()
        finally:
            condition.release()

class HTTPHandlerOne(BaseHTTPRequestHandler):
    
  def do_GET(self): 
    print("received request")
    print(self.headers)
    srange = self.headers["Range"]
    if(srange):
      print("Received range header %s" % srange)
      (low, high) = parse_range(srange)
      if(low == -1):
        low = 0
      if(high ==  -1):
        high = len(data) - 1
      print("returning values from %d to %d" % (low, high))
      if(high <= low or high >= len(data) or low < 0):
        self.wfile.write(b"HTTP/1.1 401 Bad Request\r\n")
        self.wfile.write(b"\r\n")
        return
      subdata = data[low:high+1]
      self.wfile.write(b"HTTP/1.1 206 Partial Content\r\n")
      self.wfile.write(("Content-Range: bytes=%d-%d/%d\r\n" % (low, high, len(data))).encode("utf-8"))
      self.wfile.write(("Content-Length: %d\r\n" % len(subdata)).encode("utf-8"))
      self.wfile.write(b"Content-Type: application/octet-stream\r\n")
      self.wfile.write(b"Accept-Ranges: bytes\r\n")
      self.wfile.write(b"\r\n")
      self.wfile.write(subdata)
      return

    self.wfile.write(b"HTTP/1.1 200 OK\r\n")
    self.wfile.write(b"Content-type: text/plain\r\n")
    self.wfile.write(("Content-length: %d\r\n" % len(data)).encode("utf-8"))
    self.wfile.write(b"\r\n")
    self.wfile.write(data)

def parse_range(srange):
  (prefix, frange) = srange.split("=")
  (low, hi) = frange.split("-")
  return map(to_integer, (low, hi))

def to_integer(i):
  try:
    return int(i)
  except ValueError:
    return -1

httpd = None
def run_http_server():
    server_address = ('', 8000)
    httpd = ThreadingHTTPServer(server_address, HTTPHandlerOne)
    httpd.serve_forever()
# def stop_http_server():
#     httpd.shutdown()

def http_get_data(url):
  r = requests.get(url)
  r.raise_for_status()
  return r.content

if __name__ == "__main__":
    hasher = hashlib.sha256()
    data = http_get_data("http://ota.tasmota.com/tasmota/tasmota-lite.bin")
    hasher.update(data)
    digest = hasher.hexdigest()

    zeroconf = Zeroconf()
    listener = MDNSListener()
    browser = ServiceBrowser(zeroconf, "_ewelink._tcp.local.", listener)

    try:
        while True:
            condition.acquire()
            condition.wait(20000)
            if(len(discovered)):
                print("Found a Sonoff Device in DIY mode")
                for info in discovered:
                    port = info.port
                    address = info.parsed_addresses()[0]
                    print("Connecting to %s:%d" % (address, port))
                    connection = http.client.HTTPConnection(address, port)
                    #connection = http.client.HTTPSConnection("sonoff.free.beeceptor.com")
                    headers = {'Content-type': "application/json", "Accept": "*/*"}
                    payload = json.dumps({
                                "deviceid":"",
                                    "data": {}
                                })
                    connection.request("POST", "/zeroconf/info", payload, headers)
                    response = connection.getresponse()
                    reply = json.loads(response.read().decode())
                    if( not reply["data"]["otaUnlock"]):
                        print("Unlocking OTA...")
                        connection.request("POST", "/zeroconf/ota_unlock", payload, headers)
                        response = connection.getresponse()
                        response.read()
                        status = response.status
                        if(status != 200):
                            print("Failed to unlock OTA %d", status)
                            break
                    else:
                        print("OTA already unlocked")

                    print("Starting http server")
                    thread = threading.Thread(target = run_http_server)
                    thread.start()
                    print("Sending OTA upload request")
                    hostname = socket.gethostname()
                    # ip = socket.gethostbyname(hostname)
                    downloadUrl = "http://%s:8000/tasmota.bin" % (hostname)
                    #downloadUrl = "http://ota.tasmota.com/tasmota/tasmota-lite.bin"
                    payload = json.dumps(
                        {
                            "deviceid":"",
                            "data":{
                                "downloadUrl": downloadUrl,
                                "sha256sum": digest
                                }
                        }
                    )
                    connection.request("POST", "/zeroconf/ota_flash", payload, headers)
                    response = connection.getresponse()
                    reply = json.loads(response.read().decode())
                    print(reply)
                    status = reply["error"]
                    if(status != 0):
                        print("OTA Upload request failed: %d" % status)
                    else:
                        print("OTA Upload request succeeded")
                        # stop_http_server()

                        
            condition.release()

    finally:
        zeroconf.close()
