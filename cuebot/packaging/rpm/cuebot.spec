###############################################################################
# Spec file for OpenCue Cuebot
################################################################################
Summary: OpenCue Cuebot service
Name: opencue-cuebot
Version: %rpm_version%
Release: 1
License: Apache License 2.0
URL: https://opencue.io
Group: Applications/Multimedia
Packager: Academy Software Foundation
Requires: java-1.8.0-openjdk-headless
BuildRoot: ~/rpmbuild/


%description
Cuebot typically runs on a server and performs a variety of important OpenCue management tasks, including:

 - Managing OpenCue jobs and job submissions.
 - Distributing work to render nodes.
 - Responding to API requests from client-side tools such as CueGUI.
 
A typical OpenCue deployment runs a single instance of Cuebot, which is shared by all users.


%prep
echo "BUILDROOT = $RPM_BUILD_ROOT"
mkdir -p $RPM_BUILD_ROOT/opt/opencue/cuebot/lib
mkdir -p $RPM_BUILD_ROOT/etc/sysconfig
mkdir -p $RPM_BUILD_ROOT/usr/lib/systemd/system

cp /home/rpmbuilder/LICENSE $RPM_BUILD_ROOT/opt/opencue/cuebot
cp /home/rpmbuilder/VERSION $RPM_BUILD_ROOT/opt/opencue/cuebot
cp /home/rpmbuilder/cuebot-%version%-all.jar $RPM_BUILD_ROOT/opt/opencue/cuebot/lib
cp /home/rpmbuilder/opencue-cuebot.service $RPM_BUILD_ROOT/usr/lib/systemd/system
cp /home/rpmbuilder/opencue-cuebot $RPM_BUILD_ROOT/etc/sysconfig

exit


%files
%attr(0644, root, root) /opt/opencue/cuebot/*
%attr(0644, root, root) /opt/opencue/cuebot/lib/*
%attr(0644, root, root) /usr/lib/systemd/system/opencue-cuebot.service
%attr(0600, root, root) /etc/sysconfig/opencue-cuebot


%post
ln -s -f /opt/opencue/cuebot/lib/cuebot-%version%-all.jar /opt/opencue/cuebot/lib/cuebot-latest.jar
systemctl enable opencue-cuebot.service
systemctl daemon-reload
systemctl start opencue-cuebot.service

%changelog
