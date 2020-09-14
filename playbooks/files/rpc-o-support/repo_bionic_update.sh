#!/bin/bash

cd /var/www

vers=18.1.20

wget -c http://6bc81f3e53887ce0da0b-4653baf8a5a878eb69e41270958a8060.r64.cf1.rackcdn.com/repo_r18.01_ubuntu-18.04-x86_64.tgz

tar xf repo_r18.01_ubuntu-18.04-x86_64.tgz

# remove existing symlinks/directories if present
rm -rf repo/os-releases/$vers/ubuntu-18.04-x86_64
rm -rf repo/venvs/$vers/ubuntu-18.04-x86_64

mv repo/os-releases/r18.0.1/ubuntu-18.04-x86_64 repo/os-releases/$vers/
mv repo/venvs/r18.0.1/ubuntu-18.04-x86_64 repo/venvs/$vers/

for v in repo/venvs/$vers/ubuntu-18.04-x86_64/*r18.0.1* ; do
    mv $v ${v/r18.0.1/$vers}
done

rm -rf repo/os-releases/r18.0.1 repo/venvs/r18.0.1

chown -R nginx:www-data repo/os-releases/$vers/ repo/venvs/$vers/
rm repo_r18.01_ubuntu-18.04-x86_64.tgz
