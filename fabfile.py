#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :

from cuisine import (file_exists, dir_exists, file_write, text_strip_margin,
    package_upgrade, package_clean)
from cuisine import package_ensure as _package_ensure
from cuisine import package_update as _package_update
from fabric.api import sudo, run, env, hide, cd, task
from fabric.contrib.files import append
from fabric.utils import puts
from fabric.colors import red, green

LOCAL_PREFIX = "/usr/local/bin"
INDENT = "→ "

env.user = "pi"
#env.hosts = ["rpi"]


def sudo_file_write(filename, contents):
    """ (Over)write a file as root. This is a substitute for fabric"s
    file_write for writing global configuration files.
    """
    with hide("output", "running"):
        temp_file = run("mktemp")
        file_write(temp_file, contents)
        sudo("cp -r {s} {d}".format(s=temp_file, d=filename))
        sudo("chmod 644 {}".format(filename))
        sudo("rm {}".format(temp_file))


def package_update():
    """ Pretty-printing wrapper for package_update
    """
    if not hasattr(package_update, "done"):
        puts(green("{} updating packages".format(INDENT)))
        with hide("output", "running"):
            _package_update()
        package_update.done = True


def package_ensure(package):
    """ Prettier-printing version of cuisine's package_ensure.
    Doesn't display anything if it's already been called for this package in
    this fabric session.
    """
    if not hasattr(package_ensure, "checked"):
        package_ensure.checked = []
    if package not in package_ensure.checked:
        with hide("running", "output"):
            puts("{i} checking {p}".format(i=INDENT, p=package))
            _package_ensure(package)
            package_ensure.checked.append(package)


def global_pip_install(package):
    """ Pretty-printing, internal wrapper for 'sudo pip install'.
    Doesn't bother to run if it's already been called for this package in
    this fabric session.
    """
    if not hasattr(global_pip_install, "checked"):
        global_pip_install.checked = []
    if package not in global_pip_install.checked:
        with hide("running", "output"):
            package_ensure("python-pip")
            puts("{i} checking {p}".format(i=INDENT, p=package))
            sudo("pip install {}".format(package))
            global_pip_install.checked.append(package)


@task
def install_motd():
    """ Installs a succulent ascii-art MOTD. In colour!
    The raspberry was by RPi forum user b3n, taken from
    http://www.raspberrypi.org/phpBB3/viewtopic.php?f=2&t=5494
    """

    puts(green("Installing succulent MOTD"))
    motd = text_strip_margin("""
        |
        |{g}      .~~.   .~~.
        |{g}     ". \ " " / ."
        |{r}      .~ .~~~..~.
        |{r}     : .~."~".~. :    {b}                       __                      {o}     _
        |{r}    ~ (   ) (   ) ~   {b}    _______ ____ ___  / /  ___ __________ __  {o}___  (_)
        |{r}   ( : "~".~."~" : )  {b}   / __/ _ `(_-</ _ \/ _ \/ -_) __/ __/ // / {o}/ _ \/ /
        |{r}    ~ .~ (   ) ~. ~   {p}  /_/  \_,_/___/ .__/_.__/\__/_/ /_/  \_, / {o}/ .__/_/
        |{r}     (  : "~" :  )    {p}              /_/                    /___/ {o}/_/
        |{r}      "~ .~~~. ~"
        |{r}          "~"
        |{n}
        |
        |""".format(
            g="[32m",
            r="[31m",
            b="[34m",
            o="[33m",
            p="[35m",
            n="[m",
        )
    )
    with hide("output", "running"):
        sudo_file_write("/etc/motd", motd)


@task
def setup_packages():
    """ Installs basic Raspbian package requirements.
    """
    puts(green("Installing packages"))
    package_update()

    with hide("running"):
        package_ensure("htop")
        package_ensure("bmon")
        # ... but I always use vim.
        package_ensure("vim")
        package_ensure("python-pip")


@task
def setup_kiosk_packages():
    """ Installs basic Raspbian package requirements.
    """
    puts(green("Installing packages"))
    package_update()

    with hide("running"):
        package_ensure("chromium")
        package_ensure("x11-xserver-utils")
        package_ensure("unclutter")


@task
def reboot():
    """ Reboots. Yup. """
    puts(red("Rebooting"))
    sudo("reboot")


@task
def setup_python():
    """ Installs virtualenvwrapper and some common global python packages.
    """
    puts(green("Setting up global python environment"))
    global_pip_install("ipython")
    global_pip_install("ipdb")
    global_pip_install("virtualenv")
    global_pip_install("virtualenvwrapper")
    puts("adding virtualenvwrapper to .bashrc".format(INDENT))
    with hide("everything"):
        append(".bashrc", "export WORKON_HOME=~/.virtualenvs")
        append(".bashrc", ". $(which virtualenvwrapper.sh)")


@task
def install_firewall():
    """ Installs ufw and opens ssh access to everyone.
    """
    puts(green("Installing/configuring firewall"))
    with hide("output", "running"):
        package_ensure("ufw")
        sudo("ufw allow proto tcp from any to any port 22")
        sudo("ufw --force enable")


@task
def open_port(port):
    """ Adds a firewall rule to allow EVERYONE access to the specified port.
    """
    puts(green("Configuring firewall to allow all on port {}".format(port)))
    with hide("output", "running"):
        install_firewall()
        sudo("ufw allow proto tcp from any to any port {}".format(port))
        sudo("ufw --force enable")


@task
def upgrade_packages():
    """ Pretty-printing wrapper for package_upgrade
    """
    package_update()
    puts(green("{} upgrading all packages".format(INDENT)))
    with hide("output", "running"):
        package_upgrade()
    package_clean()


@task
def status():
    """ General stats about the Pi. """
    with hide("running", "stderr"):
        run("uptime")
        run("df -h")


@task
def setup_kiosk():
    """ set up kiosk parts 
        based on https://www.danpurdy.co.uk/web-development/raspberry-pi-kiosk-screen-tutorial/
        or
        http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/gui/auto-run-browser-on-startup
    """
    with hide("running", "stderr"):
        #@xscreensaver -no-splash

        files.comment("/etc/xdg/lxsession/LXDE/autostart", "@xscreensaver -no-splash", use_sudo=True)

        files.append("/etc/xdg/lxsession/LXDE/autostart",
                     "@xset s off", use_sudo=True, escape=True)
        files.append("/etc/xdg/lxsession/LXDE/autostart",
                     "@xset -dpms", use_sudo=True, escape=True)
        files.append("/etc/xdg/lxsession/LXDE/autostart",
                     "@xset s noblank", use_sudo=True, escape=True)
                     
        files.append("/etc/xdg/lxsession/LXDE/autostart",
                     """@sed -i 's/"exited_cleanly": false/"exited_cleanly": true/' ~/.config/chromium/Default/Preferences""",
                     use_sudo=True,escape=True)

        #auto start
        if not fabric.contrib.files.contains("/etc/xdg/lxsession/LXDE/autostart",
                                             "@chromium --noerrdialogs --kiosk http://www.page-to.display --incognito",
                                             use_sudo=True, escape=True):

            files.append("/etc/xdg/lxsession/LXDE/autostart",
                         "@chromium --noerrdialogs --kiosk http://www.page-to.display --incognito",
                         use_sudo=True, escape=True)


@task
def deploy():
    """ Installs pretty much everything to a bare Pi.
    """
    puts(green("Starting deployment"))
    upgrade_packages()
    setup_packages()
    setup_kiosk_packages()
    setup_python()
    setup_kiosk()
    install_motd()
    reboot()
