FROM centos:7.2.1511

# yum-plugin-ovl - https://github.com/CentOS/sig-cloud-instance-images/issues/15
RUN yum clean all && \
    yum install -y yum-plugin-ovl && \
    yum install -y epel-release && \
    yum install -y gcc libffi-devel python-devel openssl-devel && \
    yum update -y && \
    curl -fSL 'https://bootstrap.pypa.io/get-pip.py' | python

# Copy app over
ADD . /apps/appetite

# HACK due to hardcoding in build scripts
ARG USER_ID=0

# Install and setup appetite
RUN useradd appetite_user && \
    mkdir /var/appetite && \
    cd /apps/appetite/src/ && \
    python setup.py install && \
    chown -R appetite_user: /apps/appetite/ /var/appetite

USER appetite_user

# Added aliases and symlinks
RUN appetite --help

# Added aliases and symlinks
RUN ln -s /apps/appetite ~/appetite && \
    echo 'export APPETITE_SERVER=1' >> ~/.bashrc && \
    echo 'alias appetite_test="python /apps/appetite/tests/test.py"' >> ~/.bashrc

CMD python /apps/appetite/tests/test.py


