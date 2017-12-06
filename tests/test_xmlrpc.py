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
from fs.test import *


from .utils import mock


class TestExposeXMLRPC(unittest.TestCase):

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
        cls.fs = xmlrpc_client.ServerProxy("http://%s:%s/"%(cls.host,cls.port))#,verbose=True)
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
        with self.assertRaises(Fault) as err:
            self.fs.open('/root.txt')
        assert 'fs.errors.Unsupported' in str(err.exception)

    def assert_exists(self, path):
        """Assert a path exists.

        Arguments:
            path (str): A path on the filesystem.

        """
        self.assertTrue(self.fs.exists(path))

    def assert_not_exists(self, path):
        """Assert a path does not exist.

        Arguments:
            path (str): A path on the filesystem.

        """
        self.assertFalse(self.fs.exists(path))

    def assert_isfile(self, path):
        """Assert a path is a file.

        Arguments:
            path (str): A path on the filesystem.

        """
        self.assertTrue(self.fs.isfile(path))

    def assert_isdir(self, path):
        """Assert a path is a directory.

        Arguments:
            path (str): A path on the filesystem.

        """
        self.assertTrue(self.fs.isdir(path))

    def assert_bytes(self, path, contents):
        """Assert a file contains the given bytes.

        Arguments:
            path (str): A path on the filesystem.
            contents (bytes): Bytes to compare.

        """
        assert isinstance(contents, bytes)
        data = self.fs.getbytes(path)
        self.assertEqual(data, contents)
        self.assertIsInstance(data, bytes)

    def assert_text(self, path, contents):
        """Assert a file contains the given text.

        Arguments:
            path (str): A path on the filesystem.
            contents (str): Text to compare.

        """
        assert isinstance(contents, text_type)
        with self.fs.open(path, 'rt') as f:
            data = f.read()
        self.assertEqual(data, contents)
        self.assertIsInstance(data, text_type)



    def test_appendbytes(self):
        with self.assertRaises(TypeError):
            self.fs.appendbytes('foo', 'bar')
        self.fs.appendbytes('foo', b'bar')
        self.assert_bytes('foo', b'bar')
        self.fs.appendbytes('foo', b'baz')
        self.assert_bytes('foo', b'barbaz')

    def test_appendtext(self):
        with self.assertRaises(TypeError):
            self.fs.appendtext('foo', b'bar')
        self.fs.appendtext('foo', 'bar')
        self.assert_text('foo', 'bar')
        self.fs.appendtext('foo', 'baz')
        self.assert_text('foo', 'barbaz')

    def test_basic(self):
        # Check str and repr don't break
        repr(self.fs)
        self.assertIsInstance(six.text_type(self.fs), six.text_type)

    def test_getmeta(self):
        # Get the meta dict
        meta = self.fs.getmeta()

        # Check default namespace
        self.assertEqual(meta, self.fs.getmeta(namespace="standard"))

        # Must be a dict
        self.assertTrue(isinstance(meta, dict))

        no_meta = self.fs.getmeta('__nosuchnamespace__')
        self.assertIsInstance(no_meta, dict)
        self.assertFalse(no_meta)

    def test_isfile(self):
        self.assertFalse(self.fs.isfile('foo.txt'))
        self.fs.create('foo.txt')
        self.assertTrue(self.fs.isfile('foo.txt'))
        self.fs.makedir('bar')
        self.assertFalse(self.fs.isfile('bar'))

    def test_isdir(self):
        self.assertFalse(self.fs.isdir('foo'))
        self.fs.create('bar')
        self.fs.makedir('foo')
        self.assertTrue(self.fs.isdir('foo'))
        self.assertFalse(self.fs.isdir('bar'))

    def test_islink(self):
        self.fs.touch('foo')
        self.assertFalse(self.fs.islink('foo'))
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.islink('bar')

    def test_getsize(self):
        self.fs.setbytes('empty', xmlrpclib.Binary(b''))
        self.fs.setbytes('one', xmlrpclib.Binary(b'a'))
        self.fs.setbytes('onethousand', xmlrpclib.Binary(('b' * 1000).encode('ascii')))
        self.assertEqual(self.fs.getsize('empty'), 0)
        self.assertEqual(self.fs.getsize('one'), 1)
        self.assertEqual(self.fs.getsize('onethousand'), 1000)
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.getsize('doesnotexist')

    def test_getsyspath(self):
        self.fs.create('foo')
        try:
            self.fs.getsyspath('foo')
        except errors.NoSysPath:
            self.assertFalse(self.fs.hassyspath('foo'))
        else:
            self.assertTrue(self.fs.hassyspath('foo'))

    def test_geturl(self):
        self.fs.create('foo')
        try:
            self.fs.geturl('foo')
        except errors.NoURL:
            self.assertFalse(self.fs.hasurl('foo'))
        else:
            self.assertTrue(self.fs.hasurl('foo'))

    def test_geturl_purpose(self):
        """Check an unknown purpose raises a NoURL error.
        """
        self.fs.create('foo')
        with self.assertRaises(errors.NoURL):
            self.fs.geturl('foo', '__nosuchpurpose__')

    def test_validatepath(self):
        """Check validatepath returns an absolute path.
        """
        path = self.fs.validatepath('foo')
        self.assertEqual(path, '/foo')

    def test_invalid_chars(self):
        print('Invalid chars errors could not be tested serverside')
        
        # Test invalid path method.
        # ~ with self.assertRaises(errors.InvalidCharsInPath):
            # ~ self.fs.open('invalid\0file', 'wb')

        # ~ with self.assertRaises(errors.InvalidCharsInPath):
            # ~ self.fs.validatepath('invalid\0file')


    def test_getinfo(self):
        # Test special case of root directory
        # Root directory has a name of ''

        root_info = fs.info.Info(self.fs.getinfo('/'))
        self.assertEqual(root_info.name, '')
        self.assertTrue(root_info.is_dir)

        # Make a file of known size
        self.fs.setbytes('foo', xmlrpclib.Binary(b'bar'))
        self.fs.makedir('dir')

        # Check basic namespace
        info = self.fs.getinfo('foo')
        print('Returnvalues are not unicode in python 2, not critical, should be fixed')
        # ~ self.assertIsInstance(info['basic']['name'], text_type) 

        self.assertEqual(info['basic']['name'], 'foo')
        self.assertFalse(info['basic']['is_dir'])

        # Check basic namespace dir
        info = self.fs.getinfo('dir')
        self.assertEqual(info['basic']['name'], 'dir')
        self.assertTrue(info['basic']['is_dir'])

        # Get the info
        info = self.fs.getinfo('foo', ['details'])
        self.assertIsInstance(info, dict)
        self.assertEqual(info['details']['size'], 3)
        self.assertEqual(info['details']['type'], int(ResourceType.file))

        # Test getdetails
        self.assertEqual(info, self.fs.getdetails('foo'))

        # Raw info should be serializable
        try:
            json.dumps(info)
        except:
            assert False, "info should be JSON serializable"

        # Non existant namespace is not an error
        no_info = fs.info.Info(self.fs.getinfo('foo', '__nosuchnamespace__')).raw
        self.assertIsInstance(no_info, dict)
        self.assertEqual(
            no_info['basic'],
            {'name': 'foo', 'is_dir': False}
        )

        # Check a number of standard namespaces
        # FS objects may not support all these, but we can at least
        # invoke the code
        self.fs.getinfo('foo', ['access', 'stat', 'details'])
        

    def test_exists(self):
        # Test exists method.
        # Check root directory always exists
        self.assertTrue(self.fs.exists('/'))
        self.assertTrue(self.fs.exists(''))

        # Check files don't exist
        self.assertFalse(self.fs.exists('foo'))
        self.assertFalse(self.fs.exists('foo/bar'))
        self.assertFalse(self.fs.exists('foo/bar/baz'))
        self.assertFalse(self.fs.exists('egg'))

        # make some files and directories
        self.fs.makedirs('foo/bar')
        self.fs.setbytes('foo/bar/baz', xmlrpclib.Binary(b'test'))

        # Check files exists
        self.assertTrue(self.fs.exists('foo'))
        self.assertTrue(self.fs.exists('foo/bar'))
        self.assertTrue(self.fs.exists('foo/bar/baz'))
        self.assertFalse(self.fs.exists('egg'))

        self.assert_exists('foo')
        self.assert_exists('foo/bar')
        self.assert_exists('foo/bar/baz')
        self.assert_not_exists('egg')

        # Delete a file
        self.fs.remove('foo/bar/baz')
        # Check it no longer exists
        self.assert_not_exists('foo/bar/baz')
        self.assertFalse(self.fs.exists('foo/bar/baz'))
        self.assert_not_exists('foo/bar/baz')

        # Check root directory always exists
        self.assertTrue(self.fs.exists('/'))
        self.assertTrue(self.fs.exists(''))

    def test_listdir(self):
        # Check listing directory that doesn't exist
        with self.assertRaises(Fault) as err:
            self.fs.listdir('foobar')
        assert 'fs.errors.ResourceNotFound' in str(err.exception)

        # Check aliases for root
        self.assertEqual(self.fs.listdir('/'), [])
        self.assertEqual(self.fs.listdir('.'), [])
        self.assertEqual(self.fs.listdir('./'), [])

        # Make a few files
        self.fs.setbytes('foo', xmlrpclib.Binary(b'egg'))
        self.fs.setbytes('bar', xmlrpclib.Binary(b'egg'))
        self.fs.setbytes('baz', xmlrpclib.Binary(b'egg'))

        # Check list works
        six.assertCountEqual(self,
                             self.fs.listdir('/'),
                             ['foo', 'bar', 'baz'])
        six.assertCountEqual(self,
                             self.fs.listdir('.'),
                             ['foo', 'bar', 'baz'])
        six.assertCountEqual(self,
                             self.fs.listdir('./'),
                             ['foo', 'bar', 'baz'])

        # Check paths are unicode strings 
        print('Returnvalues are not unicode in python 2, not critical, should be fixed')
        # ~ for name in self.fs.listdir('/'):
            # ~ self.assertIsInstance(name, text_type)

        # Create a subdirectory
        self.fs.makedir('dir')

        # Should start empty
        self.assertEqual(self.fs.listdir('/dir'), [])

        # Write some files
        self.fs.setbytes('dir/foofoo', xmlrpclib.Binary(b'egg'))
        self.fs.setbytes('dir/barbar', xmlrpclib.Binary(b'egg'))

        # Check listing subdirectory
        six.assertCountEqual(self,
                             self.fs.listdir('dir'),
                             ['foofoo', 'barbar'])
        # Make sure they are unicode stringd
        print('Returnvalues are not unicode in python 2, not critical, should be fixed')
        # ~ for name in self.fs.listdir('dir'):
            # ~ self.assertIsInstance(name, text_type)

        self.fs.create('notadir')
        
        with self.assertRaises(Fault) as err:
            self.fs.listdir('notadir')
        assert 'fs.errors.DirectoryExpected' in str(err.exception)

            
    def test_move(self):
        # Make a file
        self.fs.setbytes('foo', b'egg')
        self.assert_isfile('foo')

        # Move it
        self.fs.move('foo', 'bar')

        # Check it has gone from original location
        self.assert_not_exists('foo')

        # Check it exists in the new location, and contents match
        self.assert_exists('bar')
        self.assert_bytes('bar', b'egg')

        # Check moving to existing file fails
        self.fs.setbytes('foo2', b'eggegg')
        with self.assertRaises(errors.DestinationExists):
            self.fs.move('foo2', 'bar')

        # Check move with overwrite=True
        self.fs.move('foo2', 'bar', overwrite=True)
        self.assert_not_exists('foo2')

        # Check moving to a non-existant directory
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.move('bar', 'egg/bar')

        # Check moving an unexisting source
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.move('egg', 'spam')

        # Check moving between different directories
        self.fs.makedir('baz')
        self.fs.setbytes('baz/bazbaz', b'bazbaz')
        self.fs.makedir('baz2')
        self.fs.move('baz/bazbaz', 'baz2/bazbaz')
        self.assert_not_exists('baz/bazbaz')
        self.assert_bytes('baz2/bazbaz', b'bazbaz')

        # Check moving a directory raises an error
        self.assert_isdir('baz2')
        self.assert_not_exists('yolk')
        with self.assertRaises(errors.FileExpected):
            self.fs.move('baz2', 'yolk')

    def test_makedir(self):
        # Check edge case of root
        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedir('/')

        # Making root is a null op with recreate
        slash_fs = self.fs.makedir('/', recreate=True)
        self.assertIsInstance(slash_fs, SubFS)
        self.assertEqual(self.fs.listdir('/'), [])

        self.assert_not_exists('foo')
        self.fs.makedir('foo')
        self.assert_isdir('foo')
        self.assertEqual(self.fs.gettype('foo'), ResourceType.directory)
        self.fs.setbytes('foo/bar.txt', b'egg')
        self.assert_bytes('foo/bar.txt', b'egg')

        # Directory exists
        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedir('foo')

        # Parent directory doesn't exist
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.makedir('/foo/bar/baz')

        self.fs.makedir('/foo/bar')
        self.fs.makedir('/foo/bar/baz')

        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedir('foo/bar/baz')

        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedir('foo/bar.txt')

    def test_makedirs(self):
        self.assertFalse(self.fs.exists('foo'))
        self.fs.makedirs('foo')
        self.assertEqual(self.fs.gettype('foo'),
                         ResourceType.directory)

        self.fs.makedirs('foo/bar/baz')
        self.assertTrue(self.fs.isdir('foo/bar'))
        self.assertTrue(self.fs.isdir('foo/bar/baz'))

        with self.assertRaises(errors.DirectoryExists):
            self.fs.makedirs('foo/bar/baz')

        self.fs.makedirs('foo/bar/baz', recreate=True)

        self.fs.setbytes('foo.bin', b'test')
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.makedirs('foo.bin/bar')

        with self.assertRaises(errors.DirectoryExpected):
            self.fs.makedirs('foo.bin/bar/baz/egg')

    def test_repeat_dir(self):
        # Catches bug with directories contain repeated names,
        # discovered in s3fs
        self.fs.makedirs('foo/foo/foo')
        self.assertEqual(
            self.fs.listdir(u''),
            ['foo']
        )
        self.assertEqual(
            self.fs.listdir('foo'),
            ['foo']
        )
        self.assertEqual(
            self.fs.listdir('foo/foo'),
            ['foo']
        )
        self.assertEqual(
            self.fs.listdir('foo/foo/foo'),
            []
        )
        scan = list(self.fs.scandir('foo'))
        self.assertEqual(len(scan), 1)
        self.assertEqual(scan[0].name, 'foo')

    def test_open(self):
        # Open a file that doesn't exist
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.open('doesnotexist', 'r')

        self.fs.makedir('foo')

        # Create a new text file
        text = 'Hello, World'

        with self.fs.open('foo/hello', 'wt') as f:
            repr(f)
            self.assertIsInstance(f, io.IOBase)
            self.assertTrue(f.writable())
            self.assertFalse(f.readable())
            self.assertFalse(f.closed)
            f.write(text)
        self.assertTrue(f.closed)

        with self.assertRaises(errors.FileExists):
            with self.fs.open('foo/hello', 'xt') as f:
                pass

        # Read it back
        with self.fs.open('foo/hello', 'rt') as f:
            self.assertIsInstance(f, io.IOBase)
            self.assertTrue(f.readable())
            self.assertFalse(f.writable())
            self.assertFalse(f.closed)
            hello = f.read()
        self.assertTrue(f.closed)
        self.assertEqual(hello, text)
        self.assert_text('foo/hello', text)

        # Test overwrite
        text = 'Goodbye, World'
        with self.fs.open('foo/hello', 'wt') as f:
            f.write(text)
        self.assert_text('foo/hello', text)

        # Open from missing dir
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.open('/foo/bar/test.txt')

        # Test fileno returns a file number, if supported by the file.
        with self.fs.open('foo/hello') as f:
            try:
                fn = f.fileno()
            except io.UnsupportedOperation:
                pass
            else:
                self.assertEqual(os.read(fn, 7), b'Goodbye')

        # Test text files are proper iterators over themselves
        lines = os.linesep.join(["Line 1", "Line 2", "Line 3"])
        self.fs.settext("iter.txt", lines)
        with self.fs.open("iter.txt") as f:
            for actual, expected in zip(f, lines.splitlines(1)):
                self.assertEqual(actual, expected)

    def test_openbin_rw(self):
        print('openbin_rw not supported')
        # ~ # Open a file that doesn't exist
        # ~ with self.assertRaises(errors.ResourceNotFound):
            # ~ self.fs.openbin('doesnotexist', 'r')

        # ~ self.fs.makedir('foo')

        # ~ # Create a new text file
        # ~ text = b'Hello, World\n'

        # ~ with self.fs.openbin('foo/hello', 'w') as f:
            # ~ repr(f)
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertTrue(f.writable())
            # ~ self.assertFalse(f.readable())
            # ~ self.assertEqual(len(text), f.write(text))
            # ~ self.assertFalse(f.closed)
        # ~ self.assertTrue(f.closed)

        # ~ with self.assertRaises(errors.FileExists):
            # ~ with self.fs.openbin('foo/hello', 'x') as f:
                # ~ pass

        # ~ # Read it back
        # ~ with self.fs.openbin('foo/hello', 'r') as f:
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertTrue(f.readable())
            # ~ self.assertFalse(f.writable())
            # ~ hello = f.read()
            # ~ self.assertFalse(f.closed)
        # ~ self.assertTrue(f.closed)
        # ~ self.assertEqual(hello, text)
        # ~ self.assert_bytes('foo/hello', text)

        # ~ # Test overwrite
        # ~ text = b'Goodbye, World'
        # ~ with self.fs.openbin('foo/hello', 'w') as f:
            # ~ self.assertEqual(len(text), f.write(text))
        # ~ self.assert_bytes('foo/hello', text)

        # ~ # Test FileExpected raised
        # ~ with self.assertRaises(errors.FileExpected):
            # ~ self.fs.openbin('foo') #directory

        # ~ # Open from missing dir
        # ~ with self.assertRaises(errors.ResourceNotFound):
            # ~ self.fs.openbin('/foo/bar/test.txt')

        # ~ # Test fileno returns a file number, if supported by the file.
        # ~ with self.fs.openbin('foo/hello') as f:
            # ~ try:
                # ~ fn = f.fileno()
            # ~ except io.UnsupportedOperation:
                # ~ pass
            # ~ else:
                # ~ self.assertEqual(os.read(fn, 7), b'Goodbye')

        # ~ # Test binary files are proper iterators over themselves
        # ~ lines = b"\n".join([b"Line 1", b"Line 2", b"Line 3"])
        # ~ self.fs.setbytes("iter.bin", lines)
        # ~ with self.fs.openbin("iter.bin") as f:
            # ~ for actual, expected in zip(f, lines.splitlines(1)):
                # ~ self.assertEqual(actual, expected)

    def test_open_files(self):
        print('open_files not supported')
        # ~ # Test file-like objects work as expected.

        # ~ with self.fs.open('text', 'w') as f:
            # ~ repr(f)
            # ~ text_type(f)
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertTrue(f.writable())
            # ~ self.assertFalse(f.readable())
            # ~ self.assertFalse(f.closed)
            # ~ self.assertEqual(f.tell(), 0)
            # ~ f.write('Hello\nWorld\n')
            # ~ self.assertEqual(f.tell(), 12)
            # ~ f.writelines(['foo\n', 'bar\n', 'baz\n'])
            # ~ with self.assertRaises(IOError):
                # ~ f.read(1)
        # ~ self.assertTrue(f.closed)

        # ~ with self.fs.open('bin', 'wb') as f:
            # ~ with self.assertRaises(IOError):
                # ~ f.read(1)

        # ~ with self.fs.open('text', 'r') as f:
            # ~ repr(f)
            # ~ text_type(f)
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertFalse(f.writable())
            # ~ self.assertTrue(f.readable())
            # ~ self.assertFalse(f.closed)
            # ~ self.assertEqual(
                # ~ f.readlines(),
                # ~ ['Hello\n', 'World\n', 'foo\n', 'bar\n', 'baz\n']
            # ~ )
            # ~ with self.assertRaises(IOError):
                # ~ f.write('no')
        # ~ self.assertTrue(f.closed)

        # ~ with self.fs.open('text', 'rb') as f:
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertFalse(f.writable())
            # ~ self.assertTrue(f.readable())
            # ~ self.assertFalse(f.closed)
            # ~ self.assertEqual(
                # ~ f.readlines(8),
                # ~ [b'Hello\n', b'World\n']
            # ~ )
            # ~ with self.assertRaises(IOError):
                # ~ f.write('no')
        # ~ self.assertTrue(f.closed)

        # ~ with self.fs.open('text', 'r') as f:
            # ~ self.assertEqual(
                # ~ list(f),
                # ~ ['Hello\n', 'World\n', 'foo\n', 'bar\n', 'baz\n']
            # ~ )
            # ~ self.assertFalse(f.closed)
        # ~ self.assertTrue(f.closed)

        # ~ iter_lines = iter(self.fs.open('text'))
        # ~ self.assertEqual(next(iter_lines), 'Hello\n')

        # ~ with self.fs.open('unicode', 'w') as f:
            # ~ self.assertEqual(12, f.write('Héllo\nWörld\n'))

        # ~ with self.fs.open('text', 'rb') as f:
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertFalse(f.writable())
            # ~ self.assertTrue(f.readable())
            # ~ self.assertTrue(f.seekable())
            # ~ self.assertFalse(f.closed)
            # ~ self.assertEqual(f.read(1), b'H')
            # ~ self.assertEqual(3, f.seek(3, Seek.set))
            # ~ self.assertEqual(f.read(1), b'l')
            # ~ self.assertEqual(6, f.seek(2, Seek.current))
            # ~ self.assertEqual(f.read(1), b'W')
            # ~ self.assertEqual(22, f.seek(-2, Seek.end))
            # ~ self.assertEqual(f.read(1), b'z')
            # ~ with self.assertRaises(ValueError):
                # ~ f.seek(10, 77)
        # ~ self.assertTrue(f.closed)

        # ~ with self.fs.open('text', 'r+b') as f:
            # ~ self.assertIsInstance(f, io.IOBase)
            # ~ self.assertTrue(f.readable())
            # ~ self.assertTrue(f.writable())
            # ~ self.assertTrue(f.seekable())
            # ~ self.assertFalse(f.closed)
            # ~ self.assertEqual(5, f.seek(5))
            # ~ self.assertEqual(5, f.truncate())
            # ~ self.assertEqual(0, f.seek(0))
            # ~ self.assertEqual(f.read(), b'Hello')
            # ~ self.assertEqual(10, f.truncate(10))
            # ~ self.assertEqual(5, f.tell())
            # ~ self.assertEqual(0, f.seek(0))
            # ~ print(repr(self.fs))
            # ~ print(repr(f))
            # ~ self.assertEqual(f.read(), b'Hello\0\0\0\0\0')
            # ~ self.assertEqual(4, f.seek(4))
            # ~ f.write(b'O')
            # ~ self.assertEqual(4, f.seek(4))
            # ~ self.assertEqual(f.read(1), b'O')
        # ~ self.assertTrue(f.closed)

    def test_openbin(self):
        print('openbin not supported')
        # ~ # Write a binary file
        # ~ with self.fs.openbin('file.bin', 'wb') as write_file:
            # ~ repr(write_file)
            # ~ text_type(write_file)
            # ~ self.assertIsInstance(write_file, io.IOBase)
            # ~ self.assertTrue(write_file.writable())
            # ~ self.assertFalse(write_file.readable())
            # ~ self.assertFalse(write_file.closed)
            # ~ self.assertEqual(3, write_file.write(b'\0\1\2'))
        # ~ self.assertTrue(write_file.closed)

        # ~ # Read a binary file
        # ~ with self.fs.openbin('file.bin', 'rb') as read_file:
            # ~ repr(write_file)
            # ~ text_type(write_file)
            # ~ self.assertIsInstance(read_file, io.IOBase)
            # ~ self.assertTrue(read_file.readable())
            # ~ self.assertFalse(read_file.writable())
            # ~ self.assertFalse(read_file.closed)
            # ~ data = read_file.read()
        # ~ self.assertEqual(data, b'\0\1\2')
        # ~ self.assertTrue(read_file.closed)

        # ~ # Check disallow text mode
        # ~ with self.assertRaises(ValueError):
            # ~ with self.fs.openbin('file.bin', 'rt') as read_file:
                # ~ pass

        # ~ # Check errors
        # ~ with self.assertRaises(errors.ResourceNotFound):
            # ~ self.fs.openbin('foo.bin')

        # ~ # Open from missing dir
        # ~ with self.assertRaises(errors.ResourceNotFound):
            # ~ self.fs.openbin('/foo/bar/test.txt')

        # ~ self.fs.makedir('foo')
        # ~ # Attempt to open a directory
        # ~ with self.assertRaises(errors.FileExpected):
            # ~ self.fs.openbin('/foo')

        # ~ # Attempt to write to a directory
        # ~ with self.assertRaises(errors.FileExpected):
            # ~ self.fs.openbin('/foo', 'w')

        # ~ # Opening a file in a directory which doesn't exist
        # ~ with self.assertRaises(errors.ResourceNotFound):
            # ~ self.fs.openbin('/egg/bar')

        # ~ # Opening with a invalid mode
        # ~ with self.assertRaises(ValueError):
            # ~ self.fs.openbin('foo.bin', 'h')

    def test_opendir(self):
        # Make a simple directory structure
        self.fs.makedir('foo')
        self.fs.setbytes('foo/bar', b'barbar')
        self.fs.setbytes('foo/egg', b'eggegg')

        # Open a sub directory
        with self.fs.opendir('foo') as foo_fs:
            repr(foo_fs)
            text_type(foo_fs)
            six.assertCountEqual(self, foo_fs.listdir('/'), ['bar', 'egg'])
            self.assertTrue(foo_fs.isfile('bar'))
            self.assertTrue(foo_fs.isfile('egg'))
            self.assertEqual(foo_fs.getbytes('bar'), b'barbar')
            self.assertEqual(foo_fs.getbytes('egg'), b'eggegg')

        self.assertFalse(self.fs.isclosed())

        # Attempt to open a non-existent directory
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.opendir('egg')

        # Check error when doing opendir on a non dir
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.opendir('foo/egg')

        # These should work, and will essentially return a 'clone' of sorts
        self.fs.opendir('')
        self.fs.opendir('/')

        # Check ClosingSubFS closes 'parent'
        with self.fs.opendir('foo', factory=ClosingSubFS) as foo_fs:
            six.assertCountEqual(self, foo_fs.listdir('/'), ['bar', 'egg'])
            self.assertTrue(foo_fs.isfile('bar'))
            self.assertTrue(foo_fs.isfile('egg'))
            self.assertEqual(foo_fs.getbytes('bar'), b'barbar')
            self.assertEqual(foo_fs.getbytes('egg'), b'eggegg')

        self.assertTrue(self.fs.isclosed())

    def test_remove(self):

        self.fs.setbytes('foo1', b'test1')
        self.fs.setbytes('foo2', b'test2')
        self.fs.setbytes('foo3', b'test3')

        self.assert_isfile('foo1')
        self.assert_isfile('foo2')
        self.assert_isfile('foo3')

        self.fs.remove('foo2')

        self.assert_isfile('foo1')
        self.assert_not_exists('foo2')
        self.assert_isfile('foo3')

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.remove('bar')

        self.fs.makedir('dir')
        with self.assertRaises(errors.FileExpected):
            self.fs.remove('dir')

        self.fs.makedirs('foo/bar/baz/')

        error_msg = "resource 'foo/bar/egg/test.txt' not found"
        with self.assertRaisesRegexp(errors.ResourceNotFound, error_msg):
            self.fs.remove('foo/bar/egg/test.txt')

    def test_removedir(self):

        # Test removing root
        with self.assertRaises(errors.RemoveRootError):
            self.fs.removedir('/')

        self.fs.makedirs('foo/bar/baz')
        self.assertTrue(self.fs.exists('foo/bar/baz'))
        self.fs.removedir('foo/bar/baz')
        self.assertFalse(self.fs.exists('foo/bar/baz'))
        self.assertTrue(self.fs.isdir('foo/bar'))

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.removedir('nodir')

        # Test force removal
        self.fs.makedirs('foo/bar/baz')
        self.fs.setbytes('foo/egg', b'test')

        with self.assertRaises(errors.DirectoryExpected):
            self.fs.removedir('foo/egg')

        with self.assertRaises(errors.DirectoryNotEmpty):
            self.fs.removedir('foo/bar')

    def test_removetree(self):
        self.fs.makedirs('foo/bar/baz')
        self.fs.create('foo/egg.txt')
        self.fs.create('foo/bar/egg.bin')

        self.assert_exists('foo/egg.txt')
        self.assert_exists('foo/bar/egg.bin')

        self.fs.removetree('foo')
        self.assert_not_exists('foo')

    def test_setinfo(self):
        self.fs.create('birthday.txt')
        now = math.floor(time.time())

        change_info = {
            'details':
            {
                'accessed': now + 60,
                'modified': now + 60 * 60
            }
        }
        self.fs.setinfo('birthday.txt', change_info)
        new_info = self.fs.getinfo(
            'birthday.txt',
            namespaces=['details']
        ).raw
        if 'accessed' in new_info.get('_write', []):
            self.assertEqual(new_info['details']['accessed'], now + 60)
        if 'modified' in new_info.get('_write', []):
            self.assertEqual(new_info['details']['modified'], now + 60 * 60)

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.setinfo('nothing', {})

    def test_settimes(self):
        self.fs.create('birthday.txt')
        self.fs.settimes(
            'birthday.txt',
            accessed=datetime(2016, 7, 5),
        )
        info = self.fs.getinfo('birthday.txt', namespaces=['details'])
        writeable = info.get('details', '_write', [])
        if 'accessed' in writeable:
            self.assertEqual(info.accessed, datetime(2016, 7, 5, tzinfo=pytz.UTC))
        if 'modified' in writeable:
            self.assertEqual(info.modified, datetime(2016, 7, 5, tzinfo=pytz.UTC))

    def test_touch(self):
        self.fs.touch('new.txt')
        self.assert_isfile('new.txt')
        self.fs.settimes('new.txt', datetime(2016, 7, 5))
        info = self.fs.getinfo('new.txt', namespaces=['details'])
        if info.is_writeable('details', 'accessed'):
            self.assertEqual(info.accessed, datetime(2016, 7, 5, tzinfo=pytz.UTC))
            now = time.time()
            self.fs.touch('new.txt')
            accessed = self.fs.getinfo('new.txt', namespaces=['details']).raw['details']['accessed']
            self.assertTrue(accessed - now < 5)

    def test_close(self):
        self.assertFalse(self.fs.isclosed())
        self.fs.close()
        self.assertTrue(self.fs.isclosed())
        # Check second close call is a no-op
        self.fs.close()
        self.assertTrue(self.fs.isclosed())

        # Check further operations raise a FilesystemClosed exception
        with self.assertRaises(errors.FilesystemClosed):
            self.fs.openbin('test.bin')

    def test_copy(self):
        # Test copy to new path
        self.fs.setbytes('foo', b'test')
        self.fs.copy('foo', 'bar')
        self.assert_bytes('bar', b'test')

        # Test copy over existing path
        self.fs.setbytes('baz', b'truncateme')
        self.fs.copy('foo', 'baz', overwrite=True)
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

    def test_create(self):
        # Test create new file
        self.assertFalse(self.fs.exists('foo'))
        self.fs.create('foo')
        self.assertTrue(self.fs.exists('foo'))
        self.assertEqual(self.fs.gettype('foo'), ResourceType.file)
        self.assertEqual(self.fs.getsize('foo'), 0)

        # Test wipe existing file
        self.fs.setbytes('foo', b'bar')
        self.assertEqual(self.fs.getsize('foo'), 3)
        self.fs.create('foo', wipe=True)
        self.assertEqual(self.fs.getsize('foo'), 0)

        # Test create with existing file, and not wipe
        self.fs.setbytes('foo', b'bar')
        self.assertEqual(self.fs.getsize('foo'), 3)
        self.fs.create('foo', wipe=False)
        self.assertEqual(self.fs.getsize('foo'), 3)

    def test_desc(self):
        # Describe a file
        self.fs.create('foo')
        description = self.fs.desc('foo')
        self.assertIsInstance(description, text_type)

        # Describe a dir
        self.fs.makedir('dir')
        self.fs.desc('dir')

        # Special cases that may hide bugs
        self.fs.desc('/')
        self.fs.desc('')

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.desc('bar')

    def test_scandir(self):
        # Check exception for scanning dir that doesn't exist
        with self.assertRaises(errors.ResourceNotFound):
            for info in self.fs.scandir('/foobar'):
                pass

        # Check scandir returns an iterable
        iter_scandir = self.fs.scandir('/')
        self.assertTrue(isinstance(iter_scandir, collections.Iterable))
        self.assertEqual(list(iter_scandir), [])

        # Check scanning
        self.fs.create('foo')

        # Can't scandir on a file
        with self.assertRaises(errors.DirectoryExpected):
            list(self.fs.scandir('foo'))

        self.fs.create('bar')
        self.fs.makedir('dir')
        iter_scandir = self.fs.scandir('/')
        self.assertTrue(isinstance(iter_scandir, collections.Iterable))

        scandir = sorted(
            [r.raw for r in iter_scandir],
            key=lambda info: info['basic']['name']
        )

        # Filesystems may send us more than we ask for
        # We just want to test the 'basic' namespace
        scandir = [
          {'basic': i['basic']} for i in scandir
        ]

        self.assertEqual(scandir, [
            {'basic': {'name': 'bar', 'is_dir': False}},
            {'basic': {'name': 'dir', 'is_dir': True}},
            {'basic': {'name': 'foo', 'is_dir': False}},
        ])

        # Hard to test optional namespaces, but at least run the code
        list(self.fs.scandir(
            '/',
            namespaces=['details', 'link', 'stat', 'lstat', 'access']
        ))

        # Test paging
        page1 = list(self.fs.scandir('/', page=(None, 2)))
        self.assertEqual(len(page1), 2)
        page2 = list(self.fs.scandir('/', page=(2, 4)))
        self.assertEqual(len(page2), 1)
        page3 = list(self.fs.scandir('/', page=(4, 6)))
        self.assertEqual(len(page3), 0)
        paged = set(r.name for r in itertools.chain(page1, page2))
        self.assertEqual(paged, {'foo', 'bar', 'dir'})

    def test_filterdir(self):
        self.assertEqual(
            list(self.fs.filterdir('/', files=['*.py'])),
            []
        )

        self.fs.makedir('bar')
        self.fs.create('foo.txt')
        self.fs.create('foo.py')
        self.fs.create('foo.pyc')

        page1 = list(self.fs.filterdir('/', page=(None, 2)))
        page2 = list(self.fs.filterdir('/', page=(2, 4)))
        page3 = list(self.fs.filterdir('/', page=(4, 6)))

        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 2)
        self.assertEqual(len(page3), 0)
        names = [info.name for info in itertools.chain(page1, page2, page3)]
        self.assertEqual(set(names), {'foo.txt', 'foo.py', 'foo.pyc', 'bar'})

        # Check filtering by wildcard
        dir_list = [info.name for info in self.fs.filterdir('/', files=['*.py'])]
        self.assertEqual(set(dir_list), {'bar', 'foo.py'})

        # Check filtering by miltiple wildcard
        dir_list = [info.name for info in self.fs.filterdir('/', files=['*.py', '*.pyc'])]
        self.assertEqual(set(dir_list), {'bar', 'foo.py', 'foo.pyc'})

        # Check excluding dirs
        dir_list = [info.name for info in self.fs.filterdir('/', exclude_dirs=['*'], files=['*.py', '*.pyc'])]
        self.assertEqual(set(dir_list), {'foo.py', 'foo.pyc'})

        # Check excluding files
        dir_list = [info.name for info in self.fs.filterdir('/', exclude_files=['*'])]
        self.assertEqual(set(dir_list), {'bar'})

        # Check wildcards must be a list
        with self.assertRaises(TypeError):
            dir_list = [info.name for info in self.fs.filterdir('/', files="*.py")]

        self.fs.makedir('baz')
        dir_list = [info.name for info in self.fs.filterdir('/', exclude_files=['*'], dirs=['??z'])]
        self.assertEqual(set(dir_list), {'baz'})

        with self.assertRaises(TypeError):
            dir_list = [info.name for info in self.fs.filterdir('/', exclude_files=['*'], dirs="*.py")]

    def test_getbytes(self):
        # Test getbytes method.
        all_bytes = b''.join(six.int2byte(n) for n in range(256))
        with self.fs.open('foo', 'wb') as f:
            f.write(all_bytes)
        self.assertEqual(self.fs.getbytes('foo'), all_bytes)
        _all_bytes = self.fs.getbytes('foo')
        self.assertIsInstance(_all_bytes, bytes)
        self.assertEqual(_all_bytes, all_bytes)

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.getbytes('foo/bar')

        self.fs.makedir('baz')
        with self.assertRaises(errors.FileExpected):
            self.fs.getbytes('baz')

    def test_isempty(self):
        self.assertTrue(self.fs.isempty('/'))
        self.fs.makedir('foo')
        self.assertFalse(self.fs.isempty('/'))
        self.assertTrue(self.fs.isempty('/foo'))
        self.fs.create('foo/bar.txt')
        self.assertFalse(self.fs.isempty('/foo'))
        self.fs.remove('foo/bar.txt')
        self.assertTrue(self.fs.isempty('/foo'))

    def test_setbytes(self):
        all_bytes = b''.join(six.int2byte(n) for n in range(256))
        self.fs.setbytes('foo', all_bytes)
        with self.fs.open('foo', 'rb') as f:
            _bytes = f.read()
        self.assertIsInstance(_bytes, bytes)
        self.assertEqual(_bytes, all_bytes)
        self.assert_bytes('foo', all_bytes)
        with self.assertRaises(TypeError):
            self.fs.setbytes('notbytes', 'unicode')

    def test_gettext(self):
        self.fs.makedir('foo')
        with self.fs.open('foo/unicode.txt', 'wt') as f:
            f.write(UNICODE_TEXT)
        text = self.fs.gettext('foo/unicode.txt')
        self.assertIsInstance(text, text_type)
        self.assertEqual(text, UNICODE_TEXT)
        self.assert_text('foo/unicode.txt', UNICODE_TEXT)

    def test_settext(self):
        # Test settext method.
        self.fs.settext('foo', 'bar')
        with self.fs.open('foo', 'rt') as f:
            foo = f.read()
        self.assertEqual(foo, 'bar')
        self.assertIsInstance(foo, text_type)
        with self.assertRaises(TypeError):
            self.fs.settext('nottext', b'bytes')

    def test_setfile(self):
        bytes_file = io.BytesIO(b'bar')
        self.fs.setfile('foo', bytes_file)
        with self.fs.open('foo', 'rb') as f:
            data = f.read()
        self.assertEqual(data, b'bar')

    def test_setbinfile(self):
        bytes_file = io.BytesIO(b'bar')
        self.fs.setbinfile('foo', bytes_file)
        with self.fs.open('foo', 'rb') as f:
            data = f.read()
        self.assertEqual(data, b'bar')

    def test_bin_files(self):
        print('setbinfiles not suppported')
        # ~ # Check binary files.
        # ~ with self.fs.openbin('foo1', 'wb') as f:
            # ~ text_type(f)
            # ~ repr(f)
            # ~ f.write(b'a')
            # ~ f.write(b'b')
            # ~ f.write(b'c')
        # ~ self.assert_bytes('foo1', b'abc')

        # ~ # Test writelines
        # ~ with self.fs.openbin('foo2', 'wb') as f:
            # ~ f.writelines([b'hello\n', b'world'])
        # ~ self.assert_bytes('foo2', b'hello\nworld')

        # ~ # Test readline
        # ~ with self.fs.openbin('foo2') as f:
            # ~ self.assertEqual(f.readline(), b'hello\n')
            # ~ self.assertEqual(f.readline(), b'world')

        # ~ # Test readlines
        # ~ with self.fs.openbin('foo2') as f:
            # ~ lines = f.readlines()
        # ~ self.assertEqual(lines, [b'hello\n', b'world'])
        # ~ with self.fs.openbin('foo2') as f:
            # ~ lines = list(f)
        # ~ self.assertEqual(lines, [b'hello\n', b'world'])
        # ~ with self.fs.openbin('foo2') as f:
            # ~ lines = []
            # ~ for line in f:
                # ~ lines.append(line)
        # ~ self.assertEqual(lines, [b'hello\n', b'world'])
        # ~ with self.fs.openbin('foo2') as f:
            # ~ print(repr(f))
            # ~ self.assertEqual(next(f), b'hello\n')

        # ~ # Test truncate
        # ~ with self.fs.open('foo2', 'r+b') as f:
            # ~ f.truncate(3)
        # ~ self.assertEqual(self.fs.getsize('foo2'), 3)
        # ~ self.assert_bytes('foo2', b'hel')

    def test_files(self):
        # Test multiple writes

        with self.fs.open('foo1', 'wt') as f:
            text_type(f)
            repr(f)
            f.write('a')
            f.write('b')
            f.write('c')
        self.assert_text('foo1', 'abc')

        # Test writelines
        with self.fs.open('foo2', 'wt') as f:
            f.writelines(['hello\n', 'world'])
        self.assert_text('foo2', 'hello\nworld')

        # Test readline
        with self.fs.open('foo2') as f:
            self.assertEqual(f.readline(), 'hello\n')
            self.assertEqual(f.readline(), 'world')

        # Test readlines
        with self.fs.open('foo2') as f:
            lines = f.readlines()
        self.assertEqual(lines, ['hello\n', 'world'])
        with self.fs.open('foo2') as f:
            lines = list(f)
        self.assertEqual(lines, ['hello\n', 'world'])
        with self.fs.open('foo2') as f:
            lines = []
            for line in f:
                lines.append(line)
        self.assertEqual(lines, ['hello\n', 'world'])

        # Test truncate
        with self.fs.open('foo2', 'r+') as f:
            f.truncate(3)
        self.assertEqual(self.fs.getsize('foo2'), 3)
        self.assert_text('foo2', 'hel')

        with self.fs.open('foo2', 'ab') as f:
            f.write(b'p')
        self.assert_bytes('foo2', b'help')

        # Test __del__ doesn't throw traceback
        f = self.fs.open('foo2', 'r')
        del f

        with self.assertRaises(IOError):
            with self.fs.open('foo2', 'r') as f:
                f.write('no!')

        with self.assertRaises(IOError):
            with self.fs.open('newfoo', 'w') as f:
                f.read(2)

    def test_copy_file(self):
        # Test fs.copy.copy_file
        bytes_test = b'Hello, World'
        self.fs.setbytes('foo.txt', bytes_test)
        fs.copy.copy_file(self.fs, 'foo.txt', self.fs, 'bar.txt')
        self.assert_bytes('bar.txt', bytes_test)

        mem_fs = open_fs('mem://')

        fs.copy.copy_file(self.fs, 'foo.txt', mem_fs, 'bar.txt')
        self.assertEqual(mem_fs.getbytes('bar.txt'), bytes_test)

    def test_copy_structure(self):
        mem_fs = open_fs('mem://')
        self.fs.makedirs('foo/bar/baz')
        self.fs.makedir('egg')

        fs.copy.copy_structure(self.fs, mem_fs)
        expected = {
            "/egg",
            "/foo",
            "/foo/bar",
            "/foo/bar/baz",
        }
        self.assertEqual(
            set(walk.walk_dirs(mem_fs)),
            expected
        )

    def _test_copy_dir(self, protocol):
        # Test copy.copy_dir.

        # Test copying to a another fs
        other_fs = open_fs(protocol)
        self.fs.makedirs('foo/bar/baz')
        self.fs.makedir('egg')
        self.fs.settext('top.txt', 'Hello, World')
        self.fs.settext('/foo/bar/baz/test.txt', 'Goodbye, World')

        fs.copy.copy_dir(self.fs, '/', other_fs, '/')
        expected = {
            "/egg",
            "/foo",
            "/foo/bar",
            "/foo/bar/baz",
        }
        self.assertEqual(
            set(walk.walk_dirs(other_fs)),
            expected
        )
        self.assert_text('top.txt', 'Hello, World')
        self.assert_text('/foo/bar/baz/test.txt', 'Goodbye, World')

        # Test copying a sub dir
        other_fs = open_fs('mem://')
        fs.copy.copy_dir(self.fs, '/foo', other_fs, '/')
        self.assertEqual(
            list(walk.walk_files(other_fs)),
            ['/bar/baz/test.txt']
        )

        print('BEFORE')
        self.fs.tree()
        other_fs.tree()
        fs.copy.copy_dir(self.fs, '/foo', other_fs, '/egg')

        print('FS')
        self.fs.tree()
        print('OTHER')
        other_fs.tree()
        self.assertEqual(
            list(walk.walk_files(other_fs)),
            ['/bar/baz/test.txt', '/egg/bar/baz/test.txt']
        )

    def _test_copy_dir_write(self, protocol):
        # Test copying to this filesystem from another.

        other_fs = open_fs(protocol)
        other_fs.makedirs('foo/bar/baz')
        other_fs.makedir('egg')
        other_fs.settext('top.txt', 'Hello, World')
        other_fs.settext('/foo/bar/baz/test.txt', 'Goodbye, World')
        fs.copy.copy_dir(other_fs, '/', self.fs, '/')
        expected = {
            "/egg",
            "/foo",
            "/foo/bar",
            "/foo/bar/baz",
        }
        self.assertEqual(
            set(walk.walk_dirs(self.fs)),
            expected
        )
        self.assert_text('top.txt', 'Hello, World')
        self.assert_text('/foo/bar/baz/test.txt', 'Goodbye, World')

    def test_copy_dir_mem(self):
        # Test copy_dir with a mem fs.
        self._test_copy_dir('mem://')
        self._test_copy_dir_write('mem://')

    def test_copy_dir_temp(self):
        # Test copy_dir with a temp fs.
        self._test_copy_dir('temp://')
        self._test_copy_dir_write('temp://')

    def _test_move_dir_write(self, protocol):
        # Test moving to this filesystem from another.
        other_fs = open_fs(protocol)
        other_fs.makedirs('foo/bar/baz')
        other_fs.makedir('egg')
        other_fs.settext('top.txt', 'Hello, World')
        other_fs.settext('/foo/bar/baz/test.txt', 'Goodbye, World')

        fs.move.move_dir(other_fs, '/', self.fs, '/')

        expected = {
            "/egg",
            "/foo",
            "/foo/bar",
            "/foo/bar/baz",
        }
        self.assertEqual(
            other_fs.listdir('/'),
            []
        )
        self.assertEqual(
            set(walk.walk_dirs(self.fs)),
            expected
        )
        self.assert_text('top.txt', 'Hello, World')
        self.assert_text('/foo/bar/baz/test.txt', 'Goodbye, World')

    def test_move_dir_mem(self):
        self._test_move_dir_write('mem://')

    def test_move_dir_temp(self):
        self._test_move_dir_write('temp://')

    def test_move_same_fs(self):
        self.fs.makedirs('foo/bar/baz')
        self.fs.makedir('egg')
        self.fs.settext('top.txt', 'Hello, World')
        self.fs.settext('/foo/bar/baz/test.txt', 'Goodbye, World')

        fs.move.move_dir(self.fs, 'foo', self.fs, 'foo2')

        expected = {
            "/egg",
            "/foo2",
            "/foo2/bar",
            "/foo2/bar/baz",
        }
        self.assertEqual(
            set(walk.walk_dirs(self.fs)),
            expected
        )
        self.assert_text('top.txt', 'Hello, World')
        self.assert_text('/foo2/bar/baz/test.txt', 'Goodbye, World')

    def test_move_file_same_fs(self):
        text = 'Hello, World'
        self.fs.makedir('foo').settext('test.txt', text)
        self.assert_text('foo/test.txt', text)

        fs.move.move_file(self.fs, 'foo/test.txt', self.fs, 'foo/test2.txt')
        self.assert_not_exists('foo/test.txt')
        self.assert_text('foo/test2.txt', text)

    def _test_move_file(self, protocol):
        other_fs = open_fs(protocol)

        text = 'Hello, World'
        self.fs.makedir('foo').settext('test.txt', text)
        self.assert_text('foo/test.txt', text)

        with self.assertRaises(errors.ResourceNotFound):
            fs.move.move_file(self.fs, 'foo/test.txt', other_fs, 'foo/test2.txt')

        other_fs.makedir('foo')

        fs.move.move_file(self.fs, 'foo/test.txt', other_fs, 'foo/test2.txt')

        self.assertEqual(
            other_fs.gettext('foo/test2.txt'),
            text
        )

    def test_move_file_mem(self):
        self._test_move_file('mem://')

    def test_move_file_temp(self):
        self._test_move_file('temp://')

    def test_copydir(self):
        self.fs.makedirs('foo/bar/baz/egg')
        self.fs.settext('foo/bar/foofoo.txt', 'Hello')
        self.fs.makedir('foo2')
        self.fs.copydir('foo/bar', 'foo2')
        self.assert_text('foo2/foofoo.txt', 'Hello')
        self.assert_isdir('foo2/baz/egg')
        self.assert_text('foo/bar/foofoo.txt', 'Hello')
        self.assert_isdir('foo/bar/baz/egg')

        with self.assertRaises(errors.ResourceNotFound):
            self.fs.copydir('foo', 'foofoo')
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.copydir('spam', 'egg', create=True)
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.copydir('foo2/foofoo.txt', 'foofoo.txt', create=True)

    def test_movedir(self):
        self.fs.makedirs('foo/bar/baz/egg')
        self.fs.settext('foo/bar/foofoo.txt', 'Hello')
        self.fs.makedir('foo2')
        self.fs.movedir('foo/bar', 'foo2')
        self.assert_text('foo2/foofoo.txt', 'Hello')
        self.assert_isdir('foo2/baz/egg')
        self.assert_not_exists('foo/bar/foofoo.txt')
        self.assert_not_exists('foo/bar/baz/egg')

        # Check moving to an unexisting directory
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.movedir('foo', 'foofoo')

        # Check moving an unexisting directory
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.movedir('spam', 'egg', create=True)

        # Check moving a file
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.movedir('foo2/foofoo.txt', 'foo2/baz/egg')

    def test_match(self):
        self.assertTrue(self.fs.match(['*.py'], 'foo.py'))

    def test_tree(self):
        self.fs.makedirs('foo/bar')
        self.fs.create('test.txt')
        write_tree = io.StringIO()
        self.fs.tree(file=write_tree)
        written = write_tree.getvalue()
        expected = u'|-- foo\n|   `-- bar\n`-- test.txt\n'
        self.assertEqual(expected, written)

    def test_unicode_path(self):
        if not self.fs.getmeta().get('unicode_paths', False):
            self.skipTest('the filesystem does not support unicode paths.')

        self.fs.makedir('földér')
        self.fs.settext('☭.txt', 'Smells like communism.')
        self.fs.setbytes('földér/☣.txt', b'Smells like an old syringe.')

        self.assert_isdir('földér')
        self.assertEqual(['☣.txt'], self.fs.listdir('földér'))
        self.assertEqual('☣.txt', self.fs.getinfo('földér/☣.txt').name)
        self.assert_text('☭.txt', 'Smells like communism.')
        self.assert_bytes('földér/☣.txt', b'Smells like an old syringe.')

        if self.fs.hassyspath('földér/☣.txt'):
            self.assertTrue(os.path.exists(self.fs.getsyspath('földér/☣.txt')))

        self.fs.remove('földér/☣.txt')
        self.assert_not_exists('földér/☣.txt')
        self.fs.removedir('földér')
        self.assert_not_exists('földér')


    def test_case_sensitive(self):
        meta = self.fs.getmeta()
        if 'case_insensitive' not in meta:
            self.skipTest('case sensitivity not known')

        if meta.get('case_insensitive', False):
            self.skipTest('the filesystem is not case sensitive.')

        self.fs.makedir('foo')
        self.fs.makedir('Foo')
        self.fs.touch('fOO')

        self.assert_exists('foo')
        self.assert_exists('Foo')
        self.assert_exists('fOO')
        self.assert_not_exists('FoO')

        self.assert_isdir('foo')
        self.assert_isdir('Foo')
        self.assert_isfile('fOO')

