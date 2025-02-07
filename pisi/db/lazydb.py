# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import os
import pickle
import time
import pisi.context as ctx
import pisi.util as util

import string
# lower borks for international locales. What we want is ascii lower.
#lower_map = string.maketrans(string.ascii_uppercase, string.ascii_lowercase)
lower_map = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)

class Singleton(object):
    _the_instances = {}
    def __new__(type):
        if not type.__name__ in Singleton._the_instances:
            Singleton._the_instances[type.__name__] = object.__new__(type)
        return Singleton._the_instances[type.__name__]

    def _instance(self):
        return self._the_instances[type(self).__name__]

    def _delete(self):
        #FIXME: After invalidate, previously initialized db object becomes stale
        del self._the_instances[type(self).__name__]

class LazyDB(Singleton):

    cache_version = "3.0.0"

    def __init__(self, cacheable=False, cachedir=None):
        if "initialized" not in self.__dict__:
            self.initialized = False
        self.cacheable = cacheable
        self.cachedir = cachedir

    def is_initialized(self):
        return self.initialized

    def __cache_file(self):
        return util.join_path(ctx.config.cache_root_dir(), "%s.cache" % self.__class__.__name__.translate(lower_map))

    def __cache_version_file(self):
        return "%s.version" % self.__cache_file()

    def __cache_file_version(self):
        try:
            return open(self.__cache_version_file()).read().strip()
        except IOError:
            return "2.2"

    def cache_save(self):
        if os.access(ctx.config.cache_root_dir(), os.W_OK) and self.cacheable:
            with open(self.__cache_version_file(), "w") as f:
                f.write(LazyDB.cache_version)
                f.flush()
                os.fsync(f.fileno())

            pickle.dump(self._instance().__dict__,
                         open(self.__cache_file(), 'wb'), 4) # 1: binary protocol

    def cache_valid(self):
        if not self.cachedir:
            return True
        if not os.path.exists(self.cachedir):
            return False
        if self.__cache_file_version() != LazyDB.cache_version:
            return False

        cache_modified = os.stat(self.__cache_file()).st_mtime
        cache_dir_modified = os.stat(self.cachedir).st_mtime
        return cache_modified > cache_dir_modified

    def cache_load(self):
        if os.path.exists(self.__cache_file()) and self.cache_valid():
            
            try:
                # self._instance().__dict__ = pickle.load(open(self.__cache_file(), 'rb'), encoding="latin-1") # TODO: daha iyi bir encoding seçilmeli
                try:
                    self._instance().__dict__ = pickle.load(open(self.__cache_file(), 'rb'), encoding="utf-8")
                except:
                    self._instance().__dict__ = pickle.load(open(self.__cache_file(), 'rb'), encoding="latin-1")
                    # latin-1 ile okut sonra json ile çevir
                    # a=pickle.load(open("/var/cache/pisi/packagedb.cache", "rb"), encoding="latin-1")
                    # str(a).encode("utf-8")
                    # okunan veri str ye çevrildikten sonra json ile sözlüğe çevir
                return True
            except (pickle.UnpicklingError, EOFError):
                if os.access(ctx.config.cache_root_dir(), os.W_OK):
                    os.unlink(self.__cache_file())
                return False
        return False

    def cache_flush(self):
        if os.path.exists(self.__cache_file()):
            os.unlink(self.__cache_file())

    def invalidate(self):
        self._delete()

    def cache_regenerate(self):
        try:
            self.this_attr_does_not_exist()
        except AttributeError:
            pass

    def __init(self):
        if not self.cache_load():
            self.init()

    def __getattr__(self, attr):
        if not attr == "__setstate__" and not self.initialized:
            start = time.time()
            self.__init()
            end = time.time()
            ctx.ui.debug("%s initialized in %s." % (self.__class__.__name__, end - start))
            self.initialized = True

        if attr not in self.__dict__:
            raise AttributeError(attr)

        return self.__dict__[attr]
