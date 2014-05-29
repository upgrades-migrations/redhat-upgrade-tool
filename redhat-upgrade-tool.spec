Name:           redhat-upgrade-tool
Version:        0.7.19
Release:        1%{?dist}
Summary:        The Red Hat Enterprise Linux Upgrade tool
Epoch:          1

License:        GPLv2+
URL:            https://github.com/dashea/redhat-upgrade-tool
Source0:        %{name}-%{version}.tar.xz

Requires:       grubby
Requires:       python-rhsm

# Require for preupgr --riskcheck
Requires:       preupgrade-assistant >= 1.0.2-4

# https://bugzilla.redhat.com/show_bug.cgi?id=1038299
Requires:       yum >= 3.2.29-43

BuildRequires:  python-libs
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
* Thu May 29 2014 David Shea <dshea@redhat.com> 0.7.19-1
- Download RHSM product certificates (jdornak)
  Resolves: rhbz#1071902
- Workaround: Install RHSM product certificates in case that redhat-upgrade-dracut have not installed them. (jdornak)
  Resolves: rhbz#1071902

* Fri May 23 2014 David Shea <dshea@redhat.com> 0.7.18-1
- Fix the arg used with --device (bmr)
  Related: rhbz#1083169

* Fri May 23 2014 David Shea <dshea@redhat.com> 0.7.17-1
- Attempt to bring the network up during upgrade-init
  Resolves: rhbz#1089212

* Thu May 22 2014 David Shea <dshea@redhat.com> 0.7.16-1
- Run realpath on --device arguments.
  Resolves: rhbz#1083169

* Thu May 22 2014 David Shea <dshea@redhat.com> 0.7.15-1
- Add an option --cleanup-post to cleanup packages in post scripts.
  Resolves: rhbz#1070603
- Add a Requires for a sufficiently new yum
  Resolves: rhbz#1084165
- Disable screen blanking
  Resolves: rhbz#1070112
- Clear upgrade.conf before starting
  Related: rhbz#1100391
- Don't cleanup upgrade.conf for now
  Related: rhbz#1100391

* Tue May 20 2014 David Shea <dshea@redhat.com> 0.7.14-1
- Move the repo files to /etc/yum.repos.d
  Related: rhbz#1080966

* Thu May  8 2014 David Shea <dshea@redhat.com> 0.7.13-1
- Move system-upgrade.target.requires mounts into a shell script
  Resolves: rhbz#1094193

* Fri May  2 2014 David Shea <dshea@redhat.com> 0.7.12-1
- Added a check to prevent cross-variant upgrades.
  Resolves: rhbz#1070114

* Fri Apr 11 2014 David Shea <dshea@redhat.com> 0.7.11-1
- Save the repo config files to /var/tmp/system-upgrade/yum.repos.d
  Resolves: rhbz#1080966

* Thu Apr  3 2014 David Shea <dshea@redhat.com> 0.7.10-1
- Revise how preupgrade issues are printed
  Related: rhbz#1059447
- Call preupgrade-assistant API directly (phracek)
  Related: rhbz#1059447

* Thu Apr  3 2014 David Shea <dshea@redhat.com> 0.7.9-1
- Disable plymouth to workaround not reaching sysinit.target
  Resolves: rhbz#1060789
- Handle missing version arguments
  Resolves: rhbz#1069836
- Require --instrepo with --network.
  Resolves: rhbz#1070080
- Fix the reboot command for RHEL 6.
  Resolves: rhbz#1070821

* Wed Mar  5 2014 David Shea <dshea@redhat.com> 0.7.8-1
- Remove the unused systemd requires.
  Related: rhbz#1059447
- Check for preupgrade-assistant risks
  Resolves: rhbz#1059447
- Don't display package problems covered by preupgrade-assistant
  Related: rhbz#1059447
- Revise the preupgrade HIGH risk message.
  Related: rhbz#1059447

* Wed Feb 26 2014 David Shea <dshea@redhat.com> 0.7.7-1
- Remove the output parameter from CalledProcessException
  Resolves: rhbz#1054048

* Wed Feb 12 2014 David Shea <dshea@redhat.com> 0.7.6-1
- Add a generic problem summarizer.
  Resolves: rhbz#1040684
- Fix the dependency problem summary
  Related: rhbz#1040684

* Tue Jan 28 2014 David Shea <dshea@redhat.com> 0.7.5-1
- Replace subprocess backports with the versions from Python 2.7 (dshea)
  Resolves: rhbz#1054048
- Use the output of losetup to find the loop file (dshea)
  Related: rhbz#1054048
- Fix a misnamed variable in device_or_mnt (dshea)
  Related: rhbz#1054048
- fix UnboundLocalError with fedup --device (wwoods)
  Related: rhbz#1054048

* Mon Dec  2 2013 David Shea <dshea@redhat.com> 0.7.4-1
- Remove the URL from Source0
  Related: rhbz#1034906

* Tue Nov 26 2013 David Shea <dshea@redhat.com> 0.7.4-0
- Fix the kernel and initrd names. (#1031951)
- Remove rhgb quiet from the kernel command line. (#1032038)
- Remove the output parameter from CalledProcessError (#1032038)
- Change the python-devel BuildRequires to python-libs

* Tue Nov 19 2013 David Shea <dshea@redhat.com> 0.7.3-0
- Initial package for RHEL 6
  Resolves: rhbz#1012617
