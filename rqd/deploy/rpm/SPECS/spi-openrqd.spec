Name: rqd
Version: 0.21.%(date +%Y.%m.%d.%s)
Release: %{revision}
Summary: RQD module for opencue
Group: ASWF/Services
License: Apache License 2.0
Requires: protobuf3 protobuf-python gcc python-devel
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
# Required python packages: psutil PyYAML future futures grpcio

%define _use_internal_dependency_generator 0

%define _instdir /usr/local/opencue/rqd
%define _srcdir %{_instdir}/rqd

%description
RQD for opencue, runs frames when requested by the cuebot, reports periodically.
On first install it will configure it's run levels and attempt to start.
See the OpenCue Admin Guide on github for more information.

%prep
rm -rf %{name} ; mkdir %{name}
cd %{name}

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_instdir}
mkdir -p $RPM_BUILD_ROOT%{_srcdir}

cp %{_gitdir}/rqd/deploy/cudaInfo $RPM_BUILD_ROOT%{_instdir}
cp %{_gitdir}/rqd/setup.py $RPM_BUILD_ROOT%{_instdir}
cp %{_gitdir}/rqd/rqd/*.py $RPM_BUILD_ROOT%{_srcdir}
cp %{_gitdir}/rqd/rqd/__main__.py $RPM_BUILD_ROOT%{_instdir}
cp %{_gitdir}/requirements.txt $RPM_BUILD_ROOT%{_instdir}

# Build with pre-compiled proto
cp -r %{_gitdir}/rqd/rqd/compiled_proto $RPM_BUILD_ROOT%{_srcdir}
touch $RPM_BUILD_ROOT%{_srcdir}/compiled_proto/__init__.py

# Uncomment this part to build locally and compile proto at build time
#virtualenv venv
#source ./venv/bin/activate
#pip install \
# --index-url=http://pypi.spimageworks.com/spi/dev/ \
# --trusted-host=pypi.spimageworks.com -r %{_gitdir}/requirements.txt
#mkdir -p $RPM_BUILD_ROOT%{_instdir}/compiled_proto
#touch $RPM_BUILD_ROOT%{_instdir}/compiled_proto/__init__.py
#python -m grpc_tools.protoc \
#  -I=%{_gitdir}/proto \
#  --python_out=$RPM_BUILD_ROOT%{_instdir}/compiled_proto \
#  --grpc_python_out=$RPM_BUILD_ROOT%{_instdir}/compiled_proto \
#  %{_gitdir}/proto/*.proto

mkdir -p $RPM_BUILD_ROOT/etc/systemd/system
cp %{_gitdir}/rqd/deploy/opencue-rqd.service $RPM_BUILD_ROOT/etc/systemd/system/rqd.service

mkdir -p $RPM_BUILD_ROOT/etc/rqd

# Copy config file, if it hasn't been setup by puppet
cp %{_gitdir}/rqd/deploy/rqd.conf $RPM_BUILD_ROOT/etc/rqd/

%post
# Only setup and start rqd on first install
if [ $1 -eq 1 ]; then
    /sbin/chkconfig --add rqd
    /usr/bin/systemctl deamon-reload
    /usr/bin/systemctl start rqd.service
else
    echo "Not restarting rqd for upgrades"
fi

%preun
# If uninstalling (not upgrading) stop and remove rqd3
if [ $1 -eq 0 ]; then
    /usr/bin/systemctl stop rqd.service
    /sbin/chkconfig --del rqd
fi

%files
%attr(755,root,root) %{_instdir}
%attr(755,root,utmp) /etc/systemd/system/rqd.service
%attr(755,root,utmp) %config(noreplace) /etc/rqd/rqd.conf

%changelog
* Thu Jan 26 2023 Diego Tavares <dtavares@imageworks.com>
- Adapt script for opensource version
* Tue Jan 03 2023 Diego Tavares <dtavares@imageworks.com>
- Migrate service to systemd
* Wed Apr 10 2019 Diego Tavares <dtavares@imageworks.com>
- Use rqd.conf file to override configurations.
* Fri Mar 08 2019 Diego Tavares <dtavares@imageworks.com>
- Initial Version.
