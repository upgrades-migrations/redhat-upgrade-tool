Name:           rhelup
Version:        0.7.3
Release:        0%{?dist}
Summary:        The Red Hat Enterprise Linux Upgrade tool

License:        GPLv2+
URL:            https://github.com/dashea/rhelup
Source0:        https://github.com/downloads/dashea/rhelup/%{name}-%{version}.tar.xz

Requires:       grubby

%if 0%{?fedora} >= 17
# Require updates to various packages where necessary to fix bugs.
# Bug #910326
Requires:       systemd >= systemd-44-23.fc17
%endif

BuildRequires:  python2-devel
BuildRequires:  asciidoc
BuildArch:      noarch

# GET THEE BEHIND ME, SATAN
Obsoletes:      preupgrade

%description
rhelup is the Red Hat Enterprise Linux Upgrade tool.


%prep
%setup -q

%build
make PYTHON=%{__python}

%install
rm -rf $RPM_BUILD_ROOT
make install PYTHON=%{__python} DESTDIR=$RPM_BUILD_ROOT MANDIR=%{_mandir}
# backwards compatibility symlinks, wheee
ln -sf rhelup $RPM_BUILD_ROOT/%{_bindir}/rhelup-cli
ln -sf rhelup.8 $RPM_BUILD_ROOT/%{_mandir}/man8/rhelup-cli.8
# updates dir
mkdir -p $RPM_BUILD_ROOT/etc/rhelup/update.img.d



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
%{python_sitelib}/rhelup*
# binaries
%{_bindir}/rhelup
%{_bindir}/rhelup-cli
# man pages
%{_mandir}/man*/*
# empty config dir
%dir /etc/rhelup
# empty updates dir
%dir /etc/rhelup/update.img.d

#TODO - finish and package gtk-based GUI
#files gtk
#{_bindir}/rhelup-gtk
#{_datadir}/rhelup/ui

%changelog
* Tue Jul 30 2013 David Shea <dshea@redhat.com> 0.7.3-0
- Repackaged as rhelup
