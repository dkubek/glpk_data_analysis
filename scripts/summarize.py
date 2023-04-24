import sys
import csv
import argparse
import gmpy2
from pathlib import Path

VAR_FIELDS = [("var_max_bits_basic", int), ("var_bits_max_fractionality", int)]
OBJ_FIELDS = [("var_bits_total", None), ("var_bits_denom", None)]
INFO_FIELDS = [("scale", gmpy2.mpz), ("rows", int), ("cols", int),
               ("nonzeros", int), ("objective", gmpy2.mpq)]
SUMMARY_CHARACTERISTICS = ["sum", "avg", "max"]


def file_summary(file, fields):
    phase1 = {'it': 0}
    for fieldname, fieldtype in fields:
        if fieldtype is None:
            continue

        phase1[fieldname + "_sum"] = 0
        phase1[fieldname + "_avg"] = None
        phase1[fieldname + "_max"] = None

    phase2 = phase1.copy()

    with open(file, 'r') as fin:
        reading = phase1
        for line in fin:
            if line == '---\n':
                if reading['it']:
                    for fieldname, fieldtype in fields:
                        if fieldtype is None:
                            continue

                        reading[fieldname +
                                '_avg'] = (reading[fieldname + '_sum'] //
                                           reading['it'])

                reading = phase2
                continue

            values = tuple(line.split())
            for (fieldname, fieldtype), value in zip(fields, values):
                if fieldtype is None:
                    continue

                value = fieldtype(value)
                reading[fieldname + "_sum"] += value

                current = reading[fieldname + '_max']
                reading[fieldname + '_max'] = (value if current is None else
                                               max(value, current))

            reading['it'] += 1

    if reading['it']:
        for fieldname, fieldtype in fields:
            if fieldtype is None:
                continue

            reading[fieldname +
                    '_avg'] = reading[fieldname + '_sum'] // reading['it']

    return phase1, phase2


def get_var_summary(var_file):
    return file_summary(var_file, VAR_FIELDS)


def get_obj_summary(obj_file):
    return file_summary(obj_file, OBJ_FIELDS)


def read_info(info_file, fields):
    fields = dict(fields)
    info = {}
    with open(info_file, 'r') as fin:
        for line in fin:
            if "BEGIN VARIABLES" in line:
                break

            line = line.strip()
            field, value = line.split(' : ')
            if field in fields:
                info[field] = fields[field](value)

    return info


def main(data_dir, output_filename, finished=None):

    finished_instances = set()
    if finished is not None:
        with open(finished, 'r') as fin:
            finished_instances = set(
                map(lambda _: _.strip().removesuffix(".out"), fin.readlines()))

    result_files = list(data_dir.glob("*.out"))

    with open(output_filename, 'w', newline='') as csvfile:
        fieldnames = [
            "instance",
            "pivot_rule",
            "rows",
            "cols",
            "nonzeros",
            "it_p1",
            "it_p2",
            "scale",
            "objective",
        ] + [
            fieldname + f"_{sch}_p1"
            for fieldname, fieldtype in VAR_FIELDS if fieldtype is not None
            for sch in SUMMARY_CHARACTERISTICS
        ] + [
            fieldname + f"_{sch}_p2"
            for fieldname, fieldtype in VAR_FIELDS if fieldtype is not None
            for sch in SUMMARY_CHARACTERISTICS
        ] + [
            fieldname + f"_{sch}_p1"
            for fieldname, fieldtype in OBJ_FIELDS if fieldtype is not None
            for sch in SUMMARY_CHARACTERISTICS
        ] + [
            fieldname + f"_{sch}_p2"
            for fieldname, fieldtype in OBJ_FIELDS if fieldtype is not None
            for sch in SUMMARY_CHARACTERISTICS
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, filename in enumerate(result_files):
            *t, pivot_rule = filename.stem.split('.')
            basename = '.'.join(t)

            # Skip if instance has not finished
            skip = False
            if finished is None:
                with open(filename, 'r') as fin:
                    for line in fin:
                        pass
                    last_line = line

                if 'DONE' not in last_line:
                    skip = True
            else:
                if '.'.join([basename, pivot_rule]) not in finished_instances:
                    skip = True

            if skip:
                print(f"Skipping: {basename} - {pivot_rule} ")
                continue
            else:
                print(
                    f"({i}/{len(result_files)}) Processing: {basename} - {pivot_rule} ",
                    end='')

            obj_file = data_dir / '.'.join((basename, pivot_rule, "obj"))
            var_file = data_dir / '.'.join((basename, pivot_rule, "var"))
            info_file = data_dir / '.'.join((basename, pivot_rule, "info"))

            obj_phase1, obj_phase2 = get_obj_summary(obj_file)
            var_phase1, var_phase2 = get_var_summary(var_file)
            info = read_info(info_file, INFO_FIELDS)

            writer.writerow({
                "instance": basename,
                "pivot_rule": pivot_rule,
                "it_p1": obj_phase1['it'],
                "it_p2": obj_phase2['it'],
                **{field: info.get(field)
                   for field, _ in INFO_FIELDS},
                **{key + "_p1": value
                   for key, value in obj_phase1.items()},
                **{key + "_p2": value
                   for key, value in obj_phase2.items()},
                **{key + "_p1": value
                   for key, value in var_phase1.items()},
                **{key + "_p2": value
                   for key, value in var_phase2.items()},
            })

            print("DONE")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("data_dir", type=Path, help="Path to data files.")
    parser.add_argument("-o",
                        "--output_file",
                        required=False,
                        default="summary.csv",
                        type=Path,
                        help="")
    parser.add_argument("-f",
                        "--finished",
                        required=False,
                        default=None,
                        type=Path,
                        help="")

    args = parser.parse_args(sys.argv[1:])

    main(args.data_dir, args.output_file, finished=args.finished)
