# -*- coding: utf-8 -*-
#
#       util.py
#
#       Copyright 2009, 2010 Thomas Jost <thomas.jost@gmail.com>
#       Copyright 2015 Cimbali <me@cimba.li>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

"""
:mod:`pympress.util` -- various utility functions
-------------------------------------------------
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import gi
import subprocess
import importlib
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import pkg_resources
import os, os.path, sys


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


IS_POSIX = os.name == 'posix'
IS_MAC_OS = sys.platform == 'darwin'
IS_WINDOWS = os.name == 'nt'


if IS_WINDOWS:
    try:
        import winreg
    except ImportError:
        import _winreg as winreg
else:
    try:
        gi.require_version('GdkX11', '3.0')
        from gi.repository import GdkX11
    except:
        pass

try:
    PermissionError()
except NameError:
    class PermissionError(Exception):
        pass



def get_pympress_meta():
    """ Get metadata (version, etc) from pympress' __init__.py
    """
    return importlib.import_module('pympress.__init__')


def __get_resource_path(*path_parts):
    """ Return the resource path based on whether its frozen or not.
    Paths parts given should be relative to the pympress package dir.

    Args:
        name (`tuple` of `str`): The directories and filename that constitute the path
        to the resource, relative to the pympress distribution

    Returns:
        `str`: The path to the resource
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), *path_parts)
    else:
        req = pkg_resources.Requirement.parse('pympress')
        return pkg_resources.resource_filename(req, '/'.join(('pympress',) + path_parts))


def __get_resource_list(*path_parts):
    """ Return the list of elements in a directory based on whether its frozen or not.
    Paths parts given should be relative to the pympress package dir.

    Args:
        name (`tuple` of `str`): The directories that constitute the path to the resource,
        relative to the pympress distribution

    Returns:
        `list` of `str`: The paths to the resources in the directory
    """
    if getattr(sys, 'frozen', False):
        return os.listdir(os.path.join(os.path.dirname(sys.executable), *path_parts))
    else:
        req = pkg_resources.Requirement.parse('pympress')
        return pkg_resources.resource_listdir(req, '/'.join(('pympress',) + path_parts))


def get_locale_dir():
    """ Returns the path to the locale directory

    Returns:
        str: The path to the locale directory
    """
    return __get_resource_path('share', 'locale')


def get_style_provider():
    """ Load the css and return corresponding style provider.

    Returns:
        :class:`~Gtk.CssProvider`: The style provider with CSS loaded
    """
    if IS_MAC_OS:
        css_fn = __get_resource_path('share', 'css', 'macos.css')
    else:
        css_fn = __get_resource_path('share', 'css', 'default.css')

    style_provider = Gtk.CssProvider()
    style_provider.load_from_path(css_fn)
    return style_provider


def get_icon_pixbuf(name):
    """ Load an image from pympress' resources in a Gdk Pixbuf.

    Args:
        name (`str`): The name of the icon to load

    Returns:
        :class:`~GdkPixbuf.Pixbuf`: The loaded icon
    """
    return GdkPixbuf.Pixbuf.new_from_file(__get_resource_path('share', 'pixmaps', name))


def get_ui_resource_file(name):
    """ Load an UI definition file from pympress' resources.

    Args:
        name (`str`): The name of the UI to load

    Returns:
        `str`: The full path to the glade file
    """
    return __get_resource_path('share', 'xml', name + '.glade')


def list_icons():
    """ List the icons from pympress' resources.

    Returns:
        `list` of `str`: The paths to the icons in the pixmaps directory
    """
    icons = __get_resource_list('share', 'pixmaps')

    return [i for i in icons if os.path.splitext(i)[1].lower() == '.png' and i[:9] == 'pympress-']


def load_icons():
    """ Load pympress icons from the pixmaps directory (usually
    :file:`/usr/share/pixmaps` or something similar).

    Returns:
        `list` of :class:`~GdkPixbuf.Pixbuf`: loaded icons
    """
    icons = []
    for icon_name in list_icons():
        try:
            icon_pixbuf = get_icon_pixbuf(icon_name)
            icons.append(icon_pixbuf)
        except Exception as e:
            logger.exception('Error loading icons')

    return icons


def fileopen(f):
    """ Call the right function to open files, based on the platform.

    Args:
        f (`str`): path to the file to open
    """
    if IS_WINDOWS:
        os.startfile(f)
    elif IS_MAC_OS:
        subprocess.call(['open', f])
    else:
        subprocess.call(['xdg-open', f])


def set_screensaver(must_disable, window):
    """ Enable or disable the screensaver.

    Args:
        must_disable (`bool`):  if `True`, indicates that the screensaver must be disabled; otherwise it will be enabled
        window (:class:`~Gdk.Window`): The window on the screen where the screensaver is to be suspended.
    """
    if IS_MAC_OS:
        # On Mac OS X we can use caffeinate to prevent the display from sleeping
        if must_disable:
            if set_screensaver.dpms_was_enabled == None or set_screensaver.dpms_was_enabled.poll():
                set_screensaver.dpms_was_enabled = subprocess.Popen(['caffeinate', '-d', '-w', str(os.getpid())])
        else:
            if set_screensaver.dpms_was_enabled and not set_screensaver.dpms_was_enabled.poll():
                set_screensaver.dpms_was_enabled.kill()
                set_screensaver.dpms_was_enabled.poll()
                set_screensaver.dpms_was_enabled = None

    elif IS_POSIX:
        # On Linux, set screensaver with xdg-screensaver
        # (compatible with xscreensaver, gnome-screensaver and ksaver or whatever)
        cmd = "suspend" if must_disable else "resume"
        status = os.system("xdg-screensaver {} {}".format(cmd, window.get_xid()))
        if status != 0:
            logger.warning(_("Could not set screensaver status: got status ")+str(status))

        # Also manage screen blanking via DPMS
        if must_disable:
            # Get current DPMS status
            pipe = os.popen("xset q") # TODO: check if this works on all locales
            dpms_status = "Disabled"
            for line in pipe.readlines():
                if line.count("DPMS is") > 0:
                    dpms_status = line.split()[-1]
                    break
            pipe.close()

            # Set the new value correctly
            if dpms_status == "Enabled":
                set_screensaver.dpms_was_enabled = True
                status = os.system("xset -dpms")
                if status != 0:
                    logger.warning(_("Could not disable DPMS screen blanking: got status ")+str(status))
            else:
                set_screensaver.dpms_was_enabled = False

        elif set_screensaver.dpms_was_enabled:
            # Re-enable DPMS
            status = os.system("xset +dpms")
            if status != 0:
                logger.warning(_("Could not enable DPMS screen blanking: got status ")+str(status))

    elif IS_WINDOWS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Control Panel\Desktop', 0, winreg.KEY_QUERY_VALUE|winreg.KEY_SET_VALUE) as key:
                if must_disable:
                    (value,type) = winreg.QueryValueEx(key, "ScreenSaveActive")
                    assert(type == winreg.REG_SZ)
                    set_screensaver.dpms_was_enabled = (value == "1")
                    if set_screensaver.dpms_was_enabled:
                        winreg.SetValueEx(key, "ScreenSaveActive", 0, winreg.REG_SZ, "0")
                elif set_screensaver.dpms_was_enabled:
                    winreg.SetValueEx(key, "ScreenSaveActive", 0, winreg.REG_SZ, "1")
        except (OSError, PermissionError):
            logger.exception(_("access denied when trying to access screen saver settings in registry!"))
    else:
        logger.warning(_("Unsupported OS: can't enable/disable screensaver"))


#: remember DPMS setting before we change it
set_screensaver.dpms_was_enabled = None


class FileWatcher(object):
    """ A class with only static methods that wraps object watchdogs, to trigger callbacks when a file changes.
    """
    #: A :class:`~watchdog.observers.Observer` to watch when the file changes
    observer = Observer()

    #: A :class:`~watchdog.events.FileSystemEventHandler` to get notified when the file changes
    monitor = FileSystemEventHandler()

    # `int` that is a GLib timeout id to delay the callback
    timeout = 0

    @classmethod
    def watch_file(cls, path, callback, *args, **kwargs):
        """ Watches a new file with a new callback. Removes any precedent watched files.

        Args:
            path (`str`): full path to the file to watch
            callback (`function`): callback to call with all the further arguments when the file changes
        """
        cls.start_daemon()
        cls.stop_watching()

        directory = os.path.dirname(path)
        cls.monitor.on_modified = lambda evt: cls.enqueue(callback, *args, **kwargs) if evt.src_path == path else None
        try:
            cls.observer.schedule(cls.monitor, directory)
        except OSError:
            print('Impossible to open dir at {}'.format(directory))

    @classmethod
    def enqueue(cls, callback, *args, **kwargs):
        """ Do not call callback directly, instead delay as to avoid repeated calls in short periods of time.

        Args:
            callback (`function`): callback to call with all the further arguments
        """
        if cls.timeout:
            GLib.Source.remove(cls.timeout)
        cls.timeout = GLib.timeout_add(200, cls.call, callback, *args, **kwargs)


    @classmethod
    def call(cls, callback, *args, **kwargs):
        """ Call the callback

        Args:
            callback (`function`): callback to call with all the further arguments
        """
        if cls.timeout:
            cls.timeout = 0
        callback(*args, **kwargs)


    @classmethod
    def stop_watching(cls):
        """ Remove all files that are being watched
        """
        cls.observer.unschedule_all()


    @classmethod
    def start_daemon(cls):
        """ Start the watchdog observer thread
        """
        if not cls.observer.is_alive():
            cls.observer.start()


    @classmethod
    def stop_daemon(cls, wait = False):
        """ Stop the watchdog observer thread.

        Args:
            wait (`bool`): whether to wait for the thread to have joined before returning
        """
        cls.observer.unschedule_all()
        if cls.observer.is_alive():
            cls.observer.stop()

        while wait and cls.observer.is_alive():
            cls.observer.join()




##
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# py-indent-offset: 4
# fill-column: 80
# end:
