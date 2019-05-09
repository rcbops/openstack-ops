cd /var/www/repo

vers=r14.24.0

wget http://rpc-repo.rackspace.com/os-releases/$vers/ubuntu-16.04-x86_64/MANIFEST.in
grep os-release MANIFEST.in  > download
sed -i 's|^|http://rpc-repo.rackspace.com/|g' download
wget -x -i download
wget -r -l 1 http://rpc-repo.rackspace.com/venvs/$vers/ubuntu-16.04-x86_64/

mv rpc-repo.rackspace.com/os-releases/$vers/ubuntu-16.04-x86_64 os-releases/$vers/
mv rpc-repo.rackspace.com/venvs/$vers/ubuntu-16.04-x86_64 venvs/$vers/

chown -r nginx:www-data os-releases/$vers/ venvs/$vers/
rm -rf rpc-repo.rackspace.com download
