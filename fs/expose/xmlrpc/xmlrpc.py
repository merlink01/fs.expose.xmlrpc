"""
fs.expose.xmlrpc
================

Server to expose an FS via XML-RPC

This module provides the necessary infrastructure to expose an FS object
over XML-RPC.  The main class is 'RPCFSServer', a SimpleXMLRPCServer subclass
designed to expose an underlying FS.

If you need to use a more powerful server than SimpleXMLRPCServer, you can
use the RPCFSInterface class to provide an XML-RPC-compatible wrapper around
an FS object, which can then be exposed using whatever server you choose
(e.g. Twisted's XML-RPC server).

"""
from __future__ import absolute_import
from __future__ import unicode_literals


import six
from six import PY3

from six.moves.xmlrpc_server import SimpleXMLRPCServer
import six.moves.xmlrpc_client as xmlrpclib
import six.moves.cPickle as pickle

from datetime import datetime
import base64

from ... import errors
from ...path import normpath
from ...opener import open_fs

class RPCFSInterface(object):
    """Wrapper to expose an FS via a XML-RPC compatible interface.

    The only real trick is using xmlrpclib.Binary objects to transport
    the contents of files.
    """

    # info keys are restricted to a subset known to work over xmlrpc
    # This fixes an issue with transporting Longs on Py3
    _allowed_methods = [
                        "listdir",
                        "isdir",
                        "isfile",
                        "exists",
                        "getinfo",
                        "setbytes",
                        "makedir",
                        "makedirs",
                        "remove",
                        "create",
                        "touch",
                        "validatepath",
                        "islink",
                        "removetree",
                        "removedir",
                        "getbytes",
                        "getsize",
                        "isempty",
                        "move",
                        "movedir",
                        
                        "scandir",
                        "settimes",
                        "settext",
                        "setinfo",
                        "match",
                        # ~ "getsyspath",
                        "gettext",
                        # ~ "isclosed",
                        "copy",
                        "copydir",
                        "desc",
                        "appendbytes",
                        "appendtext",
                        "getmeta",
                        "gettype",
                        "getsyspath",
                        "hassyspath",
                        "geturl",
                        "hasurl",
                        "getdetails",
                        ]


    def __init__(self, fs):
        super(RPCFSInterface, self).__init__()
        self.fs = fs

    def _dispatch(self, method, params):


        if not method in self._allowed_methods:
            print('Server',method,params,'-->','Unsupported')
            raise errors.Unsupported
        
        
        # ~ return func(*params)
        #Debugging
        try: 
            func = getattr(self.fs, method)
            params = list(params)

            if six.PY2:
                # ~ if not
                if method in ['match']:
                    params[1] = params[1].decode('utf-8')
                else:
                    params[0] = params[0].decode('utf-8')
                

                if method in ['appendtext','settext']:
                    #Ugly Hack to let the Tests run through
                    try:
                        params[1] = params[1].decode('utf-8')
                    except:
                        pass
                
                if method in ['copy','move','copydir','movedir']:
                    params[1] = params[1].decode('utf-8')

                
            if method in ['setbytes','appendbytes']:
                try:
                    params[1] = params[1].data
                except:
                    print('Server',method,params,'-->','TypeError: Need an xmlrpc.Binary object')
                    raise TypeError('Need an xmlrpc.Binary object')
                    
            if method in ['settimes']:
                if isinstance(params[1], xmlrpclib.DateTime):
                    params[1] = datetime.strptime(params[1].value, "%Y%m%dT%H:%M:%S")
                if len(params) > 2:
                    if isinstance(params[2], xmlrpclib.DateTime):
                        params[2] = datetime.strptime(params[2].value, "%Y%m%dT%H:%M:%S")
                
            returndata = func(*params)

            if method in ['makedir',"makedirs"]:
                returndata = True
            
            if method in ['getinfo','getdetails']:
                returndata = returndata.raw
                
            if method in ['getbytes']:
                returndata = xmlrpclib.Binary(returndata)
                
            if method in ['getmeta']:
                if 'invalid_path_chars' in returndata:
                    # ~ print '+++++++++++++++++++++++',returndata
                    returndata['invalid_path_chars'] = xmlrpclib.Binary(returndata['invalid_path_chars'].encode('utf-8'))
            try:
                print('Server',method,params,'-->',returndata)
            except:
                pass
            return returndata
        except:
            import traceback
            print('############## Traceback from Server ####################')
            # ~ print('Server',method,params,'-->','Error')
            traceback.print_exc()
            print('############## Traceback from Server ####################')
            raise

    # ~ def encode_path(self, path):
        # ~ """Encode a filesystem path for sending over the wire.

        # ~ Unfortunately XMLRPC only supports ASCII strings, so this method
        # ~ must return something that can be represented in ASCII.  The default
        # ~ is base64-encoded UTF-8.
        # ~ """
        # ~ return path#six.text_type(base64.b64encode(path.encode("utf8")), 'ascii')

    # ~ def decode_path(self, path):
        # ~ """Decode paths arriving over the wire."""
        # ~ return six.text_type(base64.b64decode(path.encode('ascii')), 'utf8')

    # ~ def getmeta(self, meta_name):
        # ~ meta = self.fs.getmeta(meta_name)
        # ~ if isinstance(meta, basestring):
            # ~ meta = self.decode_path(meta)
        # ~ return meta

    # ~ def getmeta_default(self, meta_name, default):
        # ~ meta = self.fs.getmeta(meta_name, default)
        # ~ if isinstance(meta, basestring):
            # ~ meta = self.decode_path(meta)
        # ~ return meta

    # ~ def hasmeta(self, meta_name):
        # ~ return self.fs.hasmeta(meta_name)

    # ~ def get_contents(self, path, mode="rb"):
        # ~ path = self.decode_path(path)
        # ~ data = self.fs.getcontents(path, mode)
        # ~ return xmlrpclib.Binary(data)

    # ~ def set_contents(self, path, data):
        # ~ path = self.decode_path(path)
        # ~ self.fs.setcontents(path, data.data)

    # ~ def exists(self, path):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.exists(path)

    # ~ def isdir(self, path):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.isdir(path)

    # ~ def isfile(self, path):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.isfile(path)

    # ~ def listdir(self, path="./"):
        # ~ #path = self.decode_path(path)
        # ~ return self.fs.listdir(path)

    # ~ def makedir(self, path, recursive=False, allow_recreate=False):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.makedir(path, recursive, allow_recreate)

    # ~ def remove(self, path):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.remove(path)

    # ~ def removedir(self, path, recursive=False, force=False):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.removedir(path, recursive, force)

    # ~ def rename(self, src, dst):
        # ~ src = self.decode_path(src)
        # ~ dst = self.decode_path(dst)
        # ~ return self.fs.rename(src, dst)

    # ~ def settimes(self, path, accessed_time, modified_time):
        # ~ path = self.decode_path(path)
        # ~ if isinstance(accessed_time, xmlrpclib.DateTime):
            # ~ accessed_time = datetime.strptime(accessed_time.value, "%Y%m%dT%H:%M:%S")
        # ~ if isinstance(modified_time, xmlrpclib.DateTime):
            # ~ modified_time = datetime.strptime(modified_time.value, "%Y%m%dT%H:%M:%S")
        # ~ return self.fs.settimes(path, accessed_time, modified_time)

    # ~ def getinfo(self, path):
        # ~ path = self.decode_path(path)
        # ~ info = self.fs.getinfo(path)
        # ~ info = dict((k, v) for k, v in info.iteritems()
                    # ~ if k in self._allowed_info)
        # ~ return info

    # ~ def desc(self, path):
        # ~ path = self.decode_path(path)
        # ~ return self.fs.desc(path)

    # ~ def getxattr(self, path, attr, default=None):
        # ~ path = self.decode_path(path)
        # ~ attr = self.decode_path(attr)
        # ~ return self.fs.getxattr(path, attr, default)

    # ~ def setxattr(self, path, attr, value):
        # ~ path = self.decode_path(path)
        # ~ attr = self.decode_path(attr)
        # ~ return self.fs.setxattr(path, attr, value)

    # ~ def delxattr(self, path, attr):
        # ~ path = self.decode_path(path)
        # ~ attr = self.decode_path(attr)
        # ~ return self.fs.delxattr(path, attr)

    # ~ def listxattrs(self, path):
        # ~ path = self.decode_path(path)
        # ~ return [self.encode_path(a) for a in self.fs.listxattrs(path)]

    # ~ def copy(self, src, dst, overwrite=False, chunk_size=16384):
        # ~ src = self.decode_path(src)
        # ~ dst = self.decode_path(dst)
        # ~ return self.fs.copy(src, dst, overwrite, chunk_size)

    # ~ def move(self, src, dst, overwrite=False, chunk_size=16384):
        # ~ src = self.decode_path(src)
        # ~ dst = self.decode_path(dst)
        # ~ return self.fs.move(src, dst, overwrite, chunk_size)

    # ~ def movedir(self, src, dst, overwrite=False, ignore_errors=False, chunk_size=16384):
        # ~ src = self.decode_path(src)
        # ~ dst = self.decode_path(dst)
        # ~ return self.fs.movedir(src, dst, overwrite, ignore_errors, chunk_size)

    # ~ def copydir(self, src, dst, overwrite=False, ignore_errors=False, chunk_size=16384):
        # ~ src = self.decode_path(src)
        # ~ dst = self.decode_path(dst)
        # ~ return self.fs.copydir(src, dst, overwrite, ignore_errors, chunk_size)


class RPCFSServer(SimpleXMLRPCServer):
    """Server to expose an FS object via XML-RPC.

    This class takes as its first argument an FS instance, and as its second
    argument a (hostname,port) tuple on which to listen for XML-RPC requests.
    Example::

        fs = OSFS('/var/srv/myfiles')
        s = RPCFSServer(fs,("",8080))
        s.serve_forever()

    To cleanly shut down the server after calling serve_forever, set the
    attribute "serve_more_requests" to False.
    """
    
    def __init__(self, fs, addr, requestHandler=None, logRequests=False):
        print(addr)
        kwds = dict(allow_none=True)
        if requestHandler is not None:
            kwds['requestHandler'] = requestHandler
        if logRequests is not None:
            kwds['logRequests'] = logRequests
        self.serve_more_requests = True
        SimpleXMLRPCServer.__init__(self, addr, **kwds)
        self.register_instance(RPCFSInterface(fs))


    def serve(self):
        """Override serve_forever to allow graceful shutdown."""
        while self.serve_more_requests:
            self.handle_request()

