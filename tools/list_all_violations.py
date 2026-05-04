from rule_audit import collect_violations

def main():
    violations = collect_violations()
    for v in sorted(violations):
        print(v)

if __name__ == "__main__":
    main()
