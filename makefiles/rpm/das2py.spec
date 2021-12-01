# This spec file is for python3 only.  The reason is that das2py depends on numpy >= 1.10
# (and it really prefers 1.11 or better), but the python2 version of numpy installed
# on CentOS is 1.7.  

# Thus python2 is not intrinsically a problem, so long as you happen to have a version of
# numpy that's not ancient.

%global         srcname das2py
%global tagver  2.3-pre4

Name:           python%{python3_pkgversion}-das2py
Version:        2.3~pre4
Release:        1%{?dist}
Summary:        das2 stream utilities and catalog client in python

Group:          Development/Languages
License:        MIT
URL:            https://github.com/das-developers/%{name}

# Download the source from github automatically, normally distro maintainers
# can't do this because they have to verify source integrety.  For custom
# build RPMs of local projects this is probably okay.
#%undefine _disable_source_fetch
Source0:        https://github.com/das-developers/%{name}/archive/refs/tags/v%{tagver}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# Assume that das2C development tracks with das2py development for now so
# version numbers are the same
BuildRequires:  das2C-devel >= %{version}
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  gcc

Provides:       das2py = %{version}-%{release}
Provides:       das2py%{?_isa} = %{version}-%{release}

# Assume that das2C development tracks with das2py development for now
Requires: das2C >= %{version}
Requires: python%{python3_pkgversion}
Requires: python%{python3_pkgversion}-numpy >= 1.10

%description 
The das2py package supports downloading and parsing das2 data streams.
It is also the most full-featured das2 catalog client.  This package contains
userspace libraries and example programs. 

%prep
%setup -q -n das2py-%{tagver}

%build
%{__make} %{?_smp_mflags} PREFIX=%{_prefix} PYVER=%{python3_version} N_ARCH=/ DAS2C_LIBDIR=%{_libdir} DAS2C_INCDIR=%{_includedir}

%install
rm -rf $RPM_BUILD_ROOT
%{__install} -d -m 755 %{buildroot}%{python3_sitearch}/das2
%{__install} -d -m 755 %{buildroot}%{python3_sitearch}/das2/pycdf
%{__install} -d -m 755 %{buildroot}%{python3_sitearch}/das2/examples

%{__install} -p -m 755 build./_das2.so %{buildroot}%{python3_sitearch}
%{__install} -p -m 644 das2/*.py %{buildroot}%{python3_sitearch}/das2
%{__install} -p -m 644 das2/pycdf/*.py %{buildroot}%{python3_sitearch}/das2/pycdf
%{__install} -p -m 644 das2/pycdf/LICENSE.md %{buildroot}%{python3_sitearch}/das2/pycdf
%{__install} -p -m 644 examples/ex*.py %{buildroot}%{python3_sitearch}/das2/examples
%{__install} -p -m 644 examples/ex*.png %{buildroot}%{python3_sitearch}/das2/examples

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{python3_sitearch}/das2/examples/*.py
%{python3_sitearch}/das2/examples/*.png
%exclude %{python3_sitearch}/das2/examples/__pycache__/*
%{python3_sitearch}/_das2.so
%{python3_sitearch}/das2/*.py
%{python3_sitearch}/das2/pycdf/*.py
%{python3_sitearch}/das2/pycdf/LICENSE.md
%{python3_sitearch}/das2/__pycache__/*.pyc
%{python3_sitearch}/das2/pycdf/__pycache__/*.pyc

%changelog
* Tue Nov 30 2021 Das Developers <das-developers@uiowa.edu> - 2.3-pre4
- First das2py package
