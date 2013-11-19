Name:           redhat-upgrade-tool
Version:        0.7.3
Release:        0%{?dist}
Summary:        The Red Hat Enterprise Linux Upgrade tool
Epoch:          1

License:        GPLv2+
URL:            https://github.com/dashea/redhat-upgrade-tool
Source0:        https://github.com/downloads/dashea/redhat-upgrade-tool/%{name}-%{version}.tar.xz

Requires:       grubby

%if 0%{?fedora} >= 17
# Require updates to various packages where necessary to fix bugs.
# Bug #910326
Requires:       systemd >= systemd-44-23.fc17
%endif

BuildRequires:  python2-devel
BuildArch:      noarch

# GET THEE BEHIND ME, SATAN
Obsoletes:      preupgrade

%description
redhat-upgrade-tool is the Red Hat Enterprise Linux Upgrade tool.


%prep
%setup -q

%build
make PYTHON=%{__python}

%install
rm -rf $RPM_BUILD_ROOT
make install PYTHON=%{__python} DESTDIR=$RPM_BUILD_ROOT MANDIR=%{_mandir}
# backwards compatibility symlinks, wheee
ln -sf redhat-upgrade-tool $RPM_BUILD_ROOT/%{_bindir}/redhat-upgrade-tool-cli
ln -sf redhat-upgrade-tool.8 $RPM_BUILD_ROOT/%{_mandir}/man8/redhat-upgrade-tool-cli.8
# updates dir
mkdir -p $RPM_BUILD_ROOT/etc/redhat-upgrade-tool/update.img.d



%files
%doc README.asciidoc TODO.asciidoc COPYING
# systemd stuff
%if 0%{?_unitdir:1}
%{_unitdir}/system-upgrade.target
%{_unitdir}/upgrade-prep.service
%{_unitdir}/upgrade-switch-root.service
%{_unitdir}/upgrade-switch-root.target
%endif
# upgrade prep program
%{_libexecdir}/upgrade-prep.sh
# SysV init replacement
%{_libexecdir}/upgrade-init
# python library
%{python_sitelib}/redhat_upgrade_tool*
# binaries
%{_bindir}/redhat-upgrade-tool
%{_bindir}/redhat-upgrade-tool-cli
# man pages
%{_mandir}/man*/*
# empty config dir
%dir /etc/redhat-upgrade-tool
# empty updates dir
%dir /etc/redhat-upgrade-tool/update.img.d

#TODO - finish and package gtk-based GUI
#files gtk
#{_bindir}/redhat-upgrade-tool-gtk
#{_datadir}/redhat-upgrade-tool/ui

%changelog
* Tue Nov 19 2013 David Shea <dshea@redhat.com> 0.7.3-0
- Initial package for RHEL 6
  Resolves: rhbz#1012617
