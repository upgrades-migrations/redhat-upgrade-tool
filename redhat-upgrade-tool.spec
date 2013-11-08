Name:           redhat-upgrade-tool
Version:        0.7.3
Release:        2%{?dist}
Summary:        The Red Hat Enterprise Linux Upgrade tool
Epoch:          2

License:        GPLv2+
URL:            https://github.com/dashea/redhat-upgrade-tool
Source0:        https://github.com/downloads/dashea/redhat-upgrade-tool/%{name}-%{version}.tar.xz

# Require updates to various packages where necessary to fix bugs.
# Bug #910326
Requires:       systemd >= systemd-44-23.fc17
Requires:       grubby

BuildRequires:  python2-devel
BuildRequires:  systemd-devel
BuildRequires:  asciidoc
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
%{_unitdir}/system-upgrade.target
%{_unitdir}/upgrade-prep.service
%{_unitdir}/upgrade-switch-root.service
%{_unitdir}/upgrade-switch-root.target
# upgrade prep program
%{_libexecdir}/upgrade-prep.sh
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
* Fri Nov  8 2013 David Shea <dshea@redhat.com> - 2:0.7.3-2
- Rename to redhat-upgrade-tool
  Resolves: rhbz#1027491

* Wed Oct 30 2013 David Shea <dshea@redhat.com> - 2:0.7.3-1
- Increased the Release to satisfy version checks that omit the epoch
  Related: rhbz#1012668

* Wed Oct 30 2013 David Shea <dshea@redhat.com> - 2:0.7.3-0
- Set the epoch to 2 to provide a clean upgrade path between RHEL major versions
  Related: rhbz#1012668

* Wed Oct 23 2013 David Shea <dshea@redhat.com> - 0.7.3-0
- Initial rhelup package for RHEL 7.0 (#1012668)
