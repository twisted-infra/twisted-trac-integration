
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <sys/types.h>
#include <unistd.h>

/**
 * The user id which has access to the ssh private key.
 */
#define UID       1050

/**
 * The group id which has access to the ssh private key.
 */
#define GID       1050

/**
 * The absolute path to the rsync binary.
 */
#define RSYNC     "/usr/bin/rsync"

/**
 * The absolute path to the ssh binary.
 */
#define SSH       "/usr/bin/ssh"

/**
 * The absolute path to the private key which allows access to the remote host.
 */
#define KEY       "/home/trac/.ssh/trac@twistedmatrix.com-id_rsa"

/**
 * The absolute path to the local Subversion FSFS repository to rsync to the
 * remote host.
 */
#define REPO      "/svn/Twisted"

/**
 * The rsync destination location.
 */
#define DEST      "trac@twistedmatrix.com:svn"

/**
 * Could not format the first rsync command with the available buffer space.
 */
#define FIRST_RSYNC_FORMAT_FAILED 1

/**
 * Executing the first rsync command failed.
 */
#define FIRST_RSYNC_SYSTEM_FAILED 2

/**
 * Could not format the second rsync command with the available buffer space.
 */
#define SECOND_RSYNC_FORMAT_FAILED 3

/**
 * Executing the second rsync command failed.
 */
#define SECOND_RSYNC_SYSTEM_FAILED 4

/**
 * Changing GID failed.
 */
#define SETGID_FAILED 5

/**
 * Changing UID failed.
 */
#define SETUID_FAILED 6


/**
 * Execute the rsync commands necessary to update a remote subversion fsfs
 * repository to match the state of a local one.
 */
int main(int argc, char** argv) {
	char rsync[1024];
	int wrote;

	/**
	 * Drop root privileges and run as the user which can actually
	 * perform the rsync.  This isn't doing with setuid filesystem
	 * bits because rsync has a strange way of launching ssh which
	 * causes ssh to run as the original user when that approach is
	 * used.
	 */
	if (setgid(GID) < 0) {
		perror("setgid failed");
		return SETGID_FAILED;
	}

	if (setuid(UID) < 0) {
		perror("setuid failed");
		return SETUID_FAILED;
	}

	wrote = snprintf(
		rsync,
		sizeof rsync,
		"%s -e \"%s -i %s\" -avz --delete --exclude db/current "
		"--exclude hooks "
		"--exclude db/transactions/ \"%s\" \"%s/\"",
		RSYNC, SSH, KEY, REPO, DEST);
	if (wrote >= sizeof rsync) {
		return FIRST_RSYNC_FORMAT_FAILED;
	}

	if (system(rsync) < 0) {
		perror("first rsync");
		return FIRST_RSYNC_SYSTEM_FAILED;
	}

	wrote = snprintf(
		rsync,
		sizeof rsync,
		"%s -e \"%s -i %s\" -avz --delete --exclude db/transactions/ "
		"\"%s/db/current\" \"%s/Twisted/db/\"",
		RSYNC, SSH, KEY, REPO, DEST);

	if (wrote >= sizeof rsync) {
		return SECOND_RSYNC_FORMAT_FAILED;
	}

	if (system(rsync) < 0) {
		perror("second rsync");
		return SECOND_RSYNC_FORMAT_FAILED;
	}

	return 0;
}
