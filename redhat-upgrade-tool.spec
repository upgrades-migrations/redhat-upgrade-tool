Name:           redhat-upgrade-tool
Version:        0.9.1
Release:        1%{?dist}
Summary:        The Red Hat Enterprise Linux Upgrade tool
Epoch:          2

License:        GPLv2+
URL:            https://github.com/dashea/redhat-upgrade-tool
Source0:        %{name}-%{version}.tar.xz

# Require updates to various packages where necessary to fix bugs.
# Bug #910326
Requires:       systemd >= 44-23
Requires:       grubby

BuildRequires:  python-libs
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
* Fri Sep 19 2014 David Shea <dshea@redhat.com> - 2:0.9.1-1
- Fix the kernel and initrd names.
  Resolves: rhbz#1084143
- Change the python-devel BuildRequires to python-libs
  Related: rhbz#1084143
- Check for preupgrade-assistant risks
  Resolves: rhbz#1084145
- Don't display package problems covered by preupgrade-assistant
  Related: rhbz#1084145
- Revise the preupgrade HIGH risk message.
  Related: rhbz#1084145
- Require --instrepo with --network.
  Resolves: rhbz#1084151
- Call preupgrade-assistant API directly (phracek)
  Related: rhbz#1084145
- Revise how preupgrade issues are printed
  Related: rhbz#1084145
- Save the repo config files to /var/tmp/system-upgrade/yum.repos.d
  Resolves: rhbz#1084164
- Added a check to prevent cross-variant upgrades.
  Related: rhbz#1084145
- Move the repo files to /etc/yum.repos.d
  Related: rhbz#1084164
- Add an option --cleanup-post to cleanup packages in post scripts.
  Resolves: rhbz#1084155
- Clear upgrade.conf before starting
  Related: rhbz#1100391
- Always create the upgrade.conf directory
  Related: rhbz#1084155
- Copy upgrade.conf to /root/preupgrade
  Related: rhbz#1084155
- Fix ValueError with --addrepo/--repo REPOID (wwoods)
  Related: rhbz#1085023
- Add a message about invalid repo URLs
  Resolves: rhbz#1085023
- Catch exceptions from early treeinfo parsing
  Resolves: rhbz#1084156
- Skip preupgrade-assistant checks if preupgrade is not available
  Related: rhbz#1084145
- Fix the URLGrabError import
  Related: rhbz#1084156
- treat --network VERSION as a float, not int (wwoods)
  Related: rhbz#1084151

* Thu Jan 23 2014 David Shea <dshea@redhat.com> - 2:0.7.6-1
- Remove the URL from the Source0 line (dshea)
  Resolves: rhbz#1056730
- fix UnboundLocalError with fedup --device (wwoods)
  Resolves: rhbz#1056717

* Mon Dec 16 2013 David Shea <dshea@redhat.com> - 2:0.7.5-1
- Add a generic problem summarizer
  Resolves: rhbz#1040684

* Wed Dec 11 2013 David Shea <dshea@redhat.com> - 2:0.7.4-1
- Fix the systemd Requires: line.
  Resolves: rhbz#1035461
- Drop /run/initramfs/upgrade.conf
  Related: rhbz#1030561

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
