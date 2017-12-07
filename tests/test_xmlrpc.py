# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

__all__ = ['TestExposeXMLRPC']

import textwrap
import threading
import unittest
import base64

import six
import fs

from contextlib import closing

from fs.expose.xmlrpc import serve
from six.moves import xmlrpc_client
import six.moves.xmlrpc_client as xmlrpclib
from six.moves.xmlrpc_client import Fault
import six.moves.cPickle as pickle
from fs.errors import *
from fs import errors, info
from fs.test import *


from .utils import mock


class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
        return self.__send(self.__name, args)


class XMLRPC_Client_FS(object):
    def __init__(self, *args,**kwargs):
        self.proxy = xmlrpc_client.ServerProxy(*args,**kwargs)

    def __getattr__(self, name):
        # magic method dispatcher
        return xmlrpclib._Method(self.__request, name)

    def __call__(self, attr):
        """A workaround to get special attributes on the ServerProxy
           without interfering with the magic __getattr__
        """
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport
        raise AttributeError("Attribute %r not found" % (attr,))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.__close()



    def __request(self, methodname, params):
        
        # ~ def convert(data):
            # ~ if isinstance(data, basestring):
                # ~ return str(data)
            # ~ elif isinstance(data, collections.Mapping):
                # ~ return dict(map(convert, data.iteritems()))
            # ~ elif isinstance(data, collections.Iterable):
                # ~ return type(data)(map(convert, data))
            # ~ else:
                # ~ return data
        
        if six.PY2:
            if methodname in ['setbytes']:
                print('############',type(params[1]),params[1])
                if type(params[1]) == unicode:
                    raise TypeError('Need unicode or bytes')
        
        
        if methodname in ['setbytes','appendbytes','settext','appendtext']:
            
            if methodname in ['settext','appendtext']:
                try:
                    params[1] = params[1].decode('utf-8')
                except:
                    pass
            params = (params[0],xmlrpclib.Binary(params[1]))


        if methodname in ['getmeta']:
            if len(params) == 0:
                params = ('',)
        

        
        
        
        func = getattr(self.proxy, methodname)
        


        print(methodname, params)
        try:
            data = func(*params)
            # ~ if methodname in ['listdir','getinfo']:
                # ~ data = convert(data)
                
            if methodname in ['getinfo']:
                data = info.Info(data)
                
                
            if methodname in ['getbytes']:
                data = data.data
            if six.PY2:
                if methodname in ['listdir']:
                    outlist = []
                    for entry in data:
                        outlist.append(entry.decode('utf-8'))
                    data = outlist
            return data
        except Fault as err:
            err = str(err)
            if 'fs.errors' in err:
                x = err.split('fs.errors.')[1].split("'")[0]
                errorobj = getattr(errors, x)
                raise errorobj(err)
            if 'exceptions.TypeError' in err:

                raise TypeError(err)
            else:
                print(err)
                raise

            
        

        # ~ # call a method on the remote server
        # ~ print(methodname)

        # ~ request = xmlrpclib.dumps(params, methodname, encoding=self.__encoding,
                        # ~ allow_none=self.__allow_none).encode(self.__encoding, 'xmlcharrefreplace')

        # ~ response = self.__transport.request(
            # ~ self.__host,
            # ~ self.__handler,
            # ~ request,
            # ~ verbose=self.__verbose
            # ~ )

        # ~ if len(response) == 1:
            # ~ response = response[0]

        # ~ return response


class TestExposeXMLRPC(unittest.TestCase,FSTestCases):

# ~ class TestExposeXMLRPC(unittest.TestCase,FSTestCases):

    host = 'localhost'
    port = 8081

    # ~ @classmethod
    # ~ def _url(cls, resource):
        # ~ safe_resource = quote(resource.encode('utf-8'))
        # ~ return "http://{}:{}/{}".format(cls.host, cls.port, safe_resource)
    
    # ~ @classmethod
    # ~ def _encode_path(cls, path):
        # ~ return six.text_type(base64.b64encode(path.encode("utf8")),'ascii')

    @classmethod
    def setUpClass(cls):
        cls.test_fs = fs.open_fs('mem://')
        cls.server_thread = serve(cls.test_fs, cls.host, cls.port)
        cls.fs = XMLRPC_Client_FS("http://%s:%s/"%(cls.host,cls.port))#,verbose=True)
        print('Warning:')
        print('info objects are transfered as raw')
        print('setbytes have to be converted to xmlrpclib.Binary')
        print('getbytes have to be converted back with xmlrpcbinary.data')
        print('kwargs must be sent as args')
        

    def tearDown(self):
        self.test_fs.removetree('/')

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.shutdown()
        cls.test_fs.close()
        
    def test_unsupported(self):
        with self.assertRaises(Unsupported) as err:
            self.fs.open('/unsupported_function_test.txt')

#Officialy not supported
##############################
    @unittest.skip("Not Supported")
    def test_openbin_rw(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_open_files(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_open(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_openbin(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_bin_files(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_files(self):
        #Not Supported
        pass
    @unittest.skip("Not Supported")
    def test_close(self):
        #Not Supported
        pass

#Modified
##############################
    # ~ @unittest.skip("Ready")
    def test_getbytes(self):
        # Test getbytes method.
        all_bytes = b''.join(six.int2byte(n) for n in range(256))
        
        #Open not supported, changed Test
        self.fs.setbytes('foo',all_bytes)
        # ~ with self.fs.open('foo', 'wb') as f:
            # ~ f.write(all_bytes)
        self.assertEqual(self.fs.getbytes('foo'), all_bytes)
        _all_bytes = self.fs.getbytes('foo')
        self.assertIsInstance(_all_bytes, bytes)
        self.assertEqual(_all_bytes, all_bytes)

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.getbytes('foo/bar')

        self.fs.makedir('baz')
        with self.assertRaises(errors.FileExpected):
            self.fs.getbytes('baz')
            
    # ~ @unittest.skip("Ready")  
    def test_setbytes(self):
        all_bytes = b''.join(six.int2byte(n) for n in range(256))
        self.fs.setbytes('foo', all_bytes)
        
        #Open not supported, changed Test
        _bytes = self.fs.getbytes('foo')
        # ~ with self.fs.open('foo', 'rb') as f:
            # ~ _bytes = f.read()
        self.assertIsInstance(_bytes, bytes)
        self.assertEqual(_bytes, all_bytes)
        self.assert_bytes('foo', all_bytes)
        with self.assertRaises(TypeError):
            print('ERROR NOW')
            self.fs.setbytes('notbytes', 'unicode')
            
    # ~ @unittest.skip("Ready")
    def test_copy(self):
        # Test copy to new path
        self.fs.setbytes('foo', b'test')
        self.fs.copy('foo', 'bar')
        self.assert_bytes('bar', b'test')

        # Test copy over existing path
        self.fs.setbytes('baz', b'truncateme')
        
        #kwargs not supported, modified Test:
        self.fs.copy('foo', 'baz', True)
        # ~ self.fs.copy('foo', 'baz', overwrite=True)
        
        self.assert_bytes('foo', b'test')

        # Test copying a file to a destination that exists
        with self.assertRaises(errors.DestinationExists):
            self.fs.copy('baz', 'foo')

        # Test copying to a directory that doesn't exist
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.copy('baz', 'a/b/c/baz')

        # Test copying a source that doesn't exist
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.copy('egg', 'spam')

        # Test copying a directory
        self.fs.makedir('dir')
        with self.assertRaises(errors.FileExpected):
            self.fs.copy('dir', 'folder')
    
    # ~ @unittest.skip("Ready")
    def test_create(self):
        # Test create new file
        self.assertFalse(self.fs.exists('foo'))
        self.fs.create('foo')
        self.assertTrue(self.fs.exists('foo'))
        #Modified Test, gettype is not running now, will be fixed
        self.assertEqual(self.fs.isfile('foo'), True)
        # ~ self.assertEqual(self.fs.gettype('foo'), ResourceType.file)
        self.assertEqual(self.fs.getsize('foo'), 0)

        # Test wipe existing file
        self.fs.setbytes('foo', b'bar')
        self.assertEqual(self.fs.getsize('foo'), 3)
        #no kwargs supported
        self.fs.create('foo', True)
        # ~ self.fs.create('foo', wipe=True)
        self.assertEqual(self.fs.getsize('foo'), 0)

        # Test create with existing file, and not wipe
        self.fs.setbytes('foo', b'bar')
        self.assertEqual(self.fs.getsize('foo'), 3)
        #no kwargs supported
        self.fs.create('foo', False)
        # ~ self.fs.create('foo', wipe=False)
        self.assertEqual(self.fs.getsize('foo'), 3)
        
        
    def test_makedirs(self):
        self.assertFalse(self.fs.exists('foo'))
        self.fs.makedirs('foo')
        self.assertEqual(self.fs.isdir('foo'),
                         True)

        self.fs.makedirs('foo/bar/baz')
        self.assertTrue(self.fs.isdir('foo/bar'))
        self.assertTrue(self.fs.isdir('foo/bar/baz'))

        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedirs('foo/bar/baz')
        #no kwargs supported
        self.fs.makedirs('foo/bar/baz', True)
        # ~ self.fs.makedirs('foo/bar/baz', recreate=True)

        self.fs.setbytes('foo.bin', b'test')
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.makedirs('foo.bin/bar')

        with self.assertRaises(errors.DirectoryExpected):
            self.fs.makedirs('foo.bin/bar/baz/egg')

        
#To Check
##############################
    # ~ def test_appendtext(self):
        # ~ #Not Supported
        # ~ pass

    # ~ def test_copy_dir_mem(self):
        # ~ #Not Supported
        # ~ pass

    # ~ def test_copy_dir_temp(self):
        # ~ #Not Supported
        # ~ pass

    # ~ def test_copy_file(self):
        # ~ #Not Supported
        # ~ pass

    # ~ def test_copy_structure(self):
        # ~ #Not Supported
        # ~ pass
        
    # ~ def test_copydir(self):
        # ~ #Not Supported
        # ~ pass        
        

    # ~ def test_filterdir(self):
        # ~ #Not Supported
        # ~ pass        
             
        
    # ~ def test_getsyspath(self):
        # ~ #Not Supported
        # ~ pass        
        
    # ~ def test_gettext(self):
        # ~ #Not Supported
        # ~ pass        
        
    # ~ def test_geturl(self):
        # ~ #Not Supported
        # ~ pass        
        
    # ~ def test_invalid_chars(self):
        # ~ #Not Supported
        # ~ pass        
        
    # ~ def test_makedir(self):
        # ~ #Not Supported
        # ~ pass        
        
    # ~ def test_move(self):
        # ~ #Not Supported
        # ~ pass   
             
    # ~ def test_move_dir_mem(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_move_dir_temp(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_move_file_mem(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_move_file_same_fs(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_move_file_temp(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_move_same_fs(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_movedir(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_opendir(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_repeat_dir(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_scandir(self):
        # ~ #Not Supported
        # ~ pass             
             
    # ~ def test_setbinfile(self):
        # ~ #Not Supported
        # ~ pass               
                 
    # ~ def test_setfile(self):
        # ~ #Not Supported
        # ~ pass                 
                 
    # ~ def test_setinfo(self):
        # ~ #Not Supported
        # ~ pass                 
                 
    # ~ def test_settimes(self):
        # ~ #Not Supported
        # ~ pass                 
                 
    # ~ def test_tree(self):
        # ~ #Not Supported
        # ~ pass                 
                 
    # ~ def test_unicode_path(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_geturl_purpose(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_makedirs(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_settext(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_touch(self):
        # ~ #Not Supported
        # ~ pass   
        
    # ~ def test_match(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_appendbytes(self):
        # ~ #Not Supported
        # ~ pass   
                      
    # ~ def test_desc(self):
        # ~ #Not Supported
        # ~ pass   
        
    # ~ def test_getinfo(self):
        # ~ #Not Supported
        # ~ pass   
        
    # ~ def test_getmeta(self):  
        # ~ #Not Supported
        # ~ pass   
        

#Running
##############################
    def test_exists(self):
        pass
        
    def test_getsize(self):
        pass
        
    def test_isdir(self):
        pass
        
    def test_isempty(self):
        pass
        
    def test_isfile(self):
        pass
        
    def test_islink(self):
        pass
        
    def test_listdir(self):
        pass
        
    def test_remove(self):
        pass
        
    def test_removedir(self):
        pass
        
    def test_removetree(self):
        pass
        
    def test_validatepath(self):
        pass
        

        
        
#work:
#############################
    # ~ def test_getmeta(self):
        # ~ # Get the meta dict
        # ~ meta = self.fs.getmeta()

        # ~ # Check default namespace
        # ~ self.assertEqual(meta, self.fs.getmeta("standard"))

        # ~ # Must be a dict
        # ~ self.assertTrue(isinstance(meta, dict))

        # ~ no_meta = self.fs.getmeta('__nosuchnamespace__')
        # ~ self.assertIsInstance(no_meta, dict)
        # ~ self.assertFalse(no_meta)