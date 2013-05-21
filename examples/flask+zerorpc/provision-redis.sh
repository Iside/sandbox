#!/bin/sh

cleanup() {
    [ -n "$appdir" ] && rm -rf $appdir
}

die() {
    cleanup
    echo >&2 $*
    exit 1
}

[ $# -ne 1 ] && die "Usage: $0 <dotcloud-appname>"

type dotcloud >/dev/null || die "$0 needs a working dotCloud CLI (http://docs.dotcloud.com/firststeps/install/)"

appname="$1"
appdir=`mktemp -d`

[ -z "$appdir" ] && die "Can't create a temporary directory"

trap cleanup INT QUIT TERM

cat > "$appdir/dotcloud.yml" << EOF
db:
    type: redis
EOF

echo "$0: creating a Redis server scaled to 32M of memory in the app $appname"
yes no | dotcloud create -f live "$appname"
dotcloud push -A "$appname" "$appdir"
dotcloud scale -A "$appname" db:memory=32M

echo "$0: $appname deployed! (you can destroy it with \`dotcloud destroy -A $appname\`)"

redis_creds=`dotcloud info -A "$appname" db | grep redis: | cut -d: -f2-`

echo "$0: the Redis URL is:$redis_creds"

cleanup
