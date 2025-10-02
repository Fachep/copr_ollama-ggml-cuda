%if 0%{?fedora} >= 42
%ifarch aarch64
%bcond cuda_13 0
%else
%bcond cuda_13 1
%endif
%bcond cuda_12 1
%else
%bcond cuda_13 0
%bcond cuda_12 1
%endif
%bcond download_cuda 0
%global cuda_13_suffix 13-0
%global cuda_12_suffix 12-9
%global cuda_13_path /usr/local/cuda-13
%global cuda_12_path /usr/local/cuda-12

%ifarch aarch64
%bcond download_cuda 1
%global cuda_runfile_suffix _sbsa
%endif
%global cuda_13_url https://developer.download.nvidia.com/compute/cuda/13.0.1/local_installers/cuda_13.0.1_580.82.07_linux%{?cuda_runfile_suffix}.run
%global cuda_12_url https://developer.download.nvidia.com/compute/cuda/12.9.1/local_installers/cuda_12.9.1_575.57.08_linux%{?cuda_runfile_suffix}.run

%define _vpath_builddir %{_vendor}-%{_target_os}-build_%{ggml_preset}
%global ggml_privatelibs libggml-.*\\.so.*
%global cuda_dependencies libcublas\\.so.*|libcudart\\.so.*|libcuda\\.so.*
%global __provides_exclude_from ^(%{_libdir}/ollama/%{ggml_privatelibs})$
%global __requires_exclude ^(%{ggml_privatelibs}%{?_with_download_cuda:|%{cuda_dependencies}})$

%global ggml_license ml/backend/ggml/ggml/LICENSE

%global common_description %{expand:
Get up and running with OpenAI gpt-oss, DeepSeek-R1, Gemma 3 and other models.}

ExclusiveArch:  x86_64 aarch64

Name:           ollama-ggml-cuda
Version:        0.12.3
Release:        %autorelease
Summary:        GGML CUDA backend for ollama

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.tar.gz
# https://forums.developer.nvidia.com/t/error-exception-specification-is-incompatible-for-cospi-sinpi-cospif-sinpif-with-glibc-2-41/323591
Source1:        fix_math_functions.patch
# https://gitweb.gentoo.org/repo/gentoo.git/commit/?id=03c678f5daebb8c8004135334d18dc677a661a7b
Source2:        nvidia-cuda-toolkit-glibc-2.42.patch
Patch0:         remove-runtime-for-cuda-and-rocm.patch
Patch1:         replace-library-paths.patch

BuildRequires:  cmake
BuildRequires:  gcc-c++
%if %{with download_cuda}
BuildRequires:  wget
%endif
%if %{with cuda_13}
%if %{without download_cuda}
BuildRequires:  cuda-compiler-%{cuda_13_suffix}
BuildRequires:  cuda-libraries-devel-%{cuda_13_suffix}
BuildRequires:  cuda-nvml-devel-%{cuda_13_suffix}
%endif
Requires:       %{name}-13%{?_isa} = %{version}-%{release}
%endif

%if %{with cuda_12}
%if 0%{?fedora} >= 42
BuildRequires:  gcc14
BuildRequires:  gcc14-c++
%endif
%if %{without download_cuda}
BuildRequires:  cuda-compiler-%{cuda_12_suffix}
BuildRequires:  cuda-libraries-devel-%{cuda_12_suffix}
BuildRequires:  cuda-nvml-devel-%{cuda_12_suffix}
%endif
%if %{without cuda_13}
Requires:       %{name}-12%{?_isa} = %{version}-%{release}
%endif
%endif

%description %{common_description}
Meta-package containing GGML CUDA backend for ollama.

%prep
%autosetup -n ollama-%{version} -p1

%if %{with download_cuda}
%define install_cuda() %{expand:
wget "%{cuda_%{1}_url}" -O "%{_builddir}/cuda_%{1}.run" --retry-connrefused --tries=3 -q
chmod +x "%{_builddir}/cuda_%{1}.run"
"%{_builddir}/cuda_%{1}.run" --no-drm --no-man-page --no-opengl-libs --override --silent --toolkit --toolkitpath="%{cuda_%{1}_path}"
}

%if %{with cuda_13}
%global cuda_12_path %{_builddir}/cuda-13
%install_cuda 13
%endif

%if %{with cuda_12}
%global cuda_12_path %{_builddir}/cuda-12
%install_cuda 12
%endif
%endif

%if 0%{?with_cuda_12:%{?fedora}} >= 42
%if %{without download_cuda}
cp -a "%{cuda_12_path}/" "%{_builddir}/cuda-12/"
%global cuda_12_path %{_builddir}/cuda-12
%endif
# Fix building problem with CUDA 12 and GLIBC 2.41+
patch -p1 -d "%{cuda_12_path}"/targets/*-linux/ < %{S:1}
# Fix building problem with GLIBC 2.42+
%if %{fedora} >= 43
patch -p1 -d "%{cuda_12_path}"/targets/*-linux/ < %{S:2}
%endif
%endif

%if 0%{?with_cuda_13:%{?fedora}} >= 43
%if %{without download_cuda}
cp -a "%{cuda_13_path}/" "%{_builddir}/cuda-13/"
%global cuda_13_path %{_builddir}/cuda-13
%endif
# Fix building problem with GLIBC 2.42+
patch -p1 -d "%{cuda_13_path}"/targets/*-linux/ < %{S:2}
%endif

%build
%global cuda_flags -O2 -g -Xcompiler "-fPIC"

%if %{with cuda_13}
%global ggml_preset cuda-13
# %{?cuda_13_arches:}
%cmake --preset 'CUDA 13' -DOLLAMA_RUNNER_DIR="cuda_v13" \
    -DCMAKE_CUDA_COMPILER="%{cuda_13_path}/bin/nvcc" \
    -DCMAKE_CUDA_FLAGS_RELEASE="-DNDEBUG" \
    -DCMAKE_CUDA_FLAGS='%{cuda_flags}'
%cmake_build --target ggml-cuda
%endif

%if %{with cuda_12}
%global ggml_preset cuda-12
%cmake --preset 'CUDA 12' -DOLLAMA_RUNNER_DIR="cuda_v12" \
    -DCMAKE_CUDA_COMPILER="%{cuda_12_path}/bin/nvcc" \
%if 0%{?fedora} >= 42
    -DCMAKE_CUDA_HOST_COMPILER=g++-14 \
%endif
    -DCMAKE_CUDA_FLAGS_RELEASE="-DNDEBUG" \
    -DCMAKE_CUDA_FLAGS='%{cuda_flags}'
%cmake_build --target ggml-cuda
%endif

%install
%if %{with cuda_13}
%global ggml_preset cuda-13
%cmake_install --component "CUDA"
%endif

%if %{with cuda_12}
%global ggml_preset cuda-12
%cmake_install --component "CUDA"
%endif

%if %{with cuda_13}
%package 13
Summary:        GGML CUDA 13 backend for ollama
Requires:       ollama-ggml%{?_isa} = %{version}
Supplements:    ollama-ggml if libcublas-%{cuda_13_suffix}
%description 13 %{common_description}
This package contains the GGML CUDA 13 backend for ollama.

%files 13
%license %{ggml_license}
%{_libdir}/ollama/cuda_v13/libggml-cuda.so
%endif

%if %{with cuda_12}
%package 12
Summary:        GGML CUDA 12 backend for ollama
Requires:       ollama-ggml%{?_isa} = %{version}
Supplements:    ollama-ggml if libcublas-%{cuda_12_suffix}
%description 12 %{common_description}
This package contains the GGML CUDA 12 backend for ollama.

%files 12
%license %{ggml_license}
%{_libdir}/ollama/cuda_v12/libggml-cuda.so
%endif

%changelog
%autochangelog
