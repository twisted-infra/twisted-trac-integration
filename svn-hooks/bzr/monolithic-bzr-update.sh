#!/bin/bash -ex
REMOTE_BASE_URL="svn://svn.twistedmatrix.com/svn/Twisted"
MIRROR_ROOT=~www-data/bzr/Twisted

pushd ${MIRROR_ROOT}

pushd trunk
bzr pull ${REMOTE_BASE_URL}/trunk
popd

pushd branches

# Update or add remote branches.
remote_branches=`svn ls ${REMOTE_BASE_URL}/branches | sed -e '/^releases\//d'`
remote_release_branches=`svn ls ${REMOTE_BASE_URL}/branches/releases | sed -e 's,^,releases/,'`
for remote_branch in $remote_branches $remote_release_branches
do
        # Skip the directory containing release branches - it, itself, is not a branch.
        if [ $remote_branch == "releases" ]; then
                continue
        fi

        if [ -d ./$remote_branch ]; then
                pushd ./$remote_branch > /dev/null
                        echo '* Updating' `pwd`
                        bzr pull ${REMOTE_BASE_URL}/branches/$remote_branch
                popd > /dev/null
        else
                echo '+ Creating' `pwd`/$remote_branch 
                bzr branch ${REMOTE_BASE_URL}/branches/$remote_branch ./$remote_branch
        fi
done

# Delete local branches that are no longer used on the server.
local_branches=`ls -1`
local_release_branches=`ls -1 releases | sed -e 's,^,releases/,'`
for local_branch in $local_branches $local_release_branches
do
        # Skip the directory containing release branches - it, itself, is not a branch.
        if [ $local_branch == "releases" ]; then
                continue
        fi
        if [[ $remote_branches == *$local_branch* ]]; then
                echo '* Branch exists' `pwd`/$local_branch
        else
                echo '- Removing' `pwd`/$local_branch
                rm -rf ./$local_branch
        fi
done

popd
