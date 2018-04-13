PYTHON=python
VERSION=0.7.51
RPMDIR_PATH=${PWD}

all: build

SUBDIRS := systemd man
$(SUBDIRS):
	$(MAKE) -C $@

INSTALL_TARGETS = $(SUBDIRS:%=install-%)
$(INSTALL_TARGETS):
	$(MAKE) -C $(@:install-%=%) install

CLEAN_TARGETS = $(SUBDIRS:%=clean-%)
$(CLEAN_TARGETS):
	$(MAKE) -C $(@:clean-%=%) clean

build: $(SUBDIRS)
	$(PYTHON) setup.py build

test:
	nosetests -v --nocapture

test-all:
	tox


install: all $(INSTALL_TARGETS)
	$(PYTHON) setup.py install --skip-build --root $(DESTDIR)/

clean: $(CLEAN_TARGETS)
	$(PYTHON) setup.py clean
	rm -rf build sdist SRPMS BUILD RPMS
	rm -f $(ARCHIVE)

ARCHIVE = redhat-upgrade-tool-$(VERSION).tar.xz
archive: $(ARCHIVE)
redhat-upgrade-tool-$(VERSION).tar.xz:
	git archive --format=tar --prefix=redhat-upgrade-tool-$(VERSION)/ HEAD \
	  | xz -c > $@ || rm $@

prep:
	$(PYTHON) setup.py sdist --formats=gztar

srpm: prep
	rpmbuild -bs redhat-upgrade-tool.spec \
		--define "_sourcedir $(RPMDIR_PATH)/dist"  \
		--define "_srcrpmdir $(RPMDIR_PATH)/SRPMS" \
		--define '_builddir  $(RPMDIR_PATH)/BUILD' \
		--define '_rpmdir    $(RPMDIR_PATH)/RPMS'  \
		--define "rhel 6"    \
		--define 'dist .el6' \
		--define 'el6 1'


local_rpm_build: prep
	rpmbuild -ba redhat-upgrade-tool.spec \
		--define "_sourcedir $(RPMDIR_PATH)/dist"  \
		--define "_srcrpmdir $(RPMDIR_PATH)/SRPMS" \
		--define '_builddir  $(RPMDIR_PATH)/BUILD' \
		--define '_rpmdir    $(RPMDIR_PATH)/RPMS'  \
		--define "rhel 6"    \
		--define 'dist .el6' \
		--define 'el6 1'


.PHONY: all archive install clean
.PHONY: $(SUBDIRS) $(INSTALL_TARGETS) $(CLEAN_TARGETS)
