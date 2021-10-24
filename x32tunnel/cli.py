import logging
import argparse

import x32tunnel.client_side
import x32tunnel.mixer_side


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', '-q', action='count', default=0)
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--tunnel-port', '-p', default=10024)
    
    subparsers = parser.add_subparsers(dest="side")

    client_side = subparsers.add_parser("client-side")
    client_side.add_argument('--tunnel-host', '-H', default='localhost')
    client_side.add_argument('--udp-bind-host', default='0.0.0.0')

    mixer_side = subparsers.add_parser("mixer-side")
    mixer_side.add_argument('--mixer-host', '-m', default='mixer')
    mixer_side.add_argument('--filter', '-f', action='append')
    mixer_side.add_argument('--rate-limit', '-R', type=float, default=1.0)
    mixer_side.add_argument('--rate-limits', '-r', action='append', default=['meters'])
    
    return parser.parse_args()


def main():
    args = parse_args()

    # configure logging
    log_level = max(0, (logging.INFO + (10 * args.quiet) - (10 * args.verbose)))
    log_line = "%(message)s"
    if args.verbose >= 3:
        log_line = "%(name)s.%(funcName)s:%(lineno)d %(message)s"
    logging.basicConfig(
        format='[%(levelname)s] ' + log_line,
        level=log_level
    )
    
    if args.side == "client-side":
        x32tunnel.client_side.main_loop(args)
    elif args.side == "mixer-side":
        x32tunnel.mixer_side.main_loop(args)


if __name__ == "__main__":
    main()
