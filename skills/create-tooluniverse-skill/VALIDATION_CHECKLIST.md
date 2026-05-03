# Validation Checklist

Complete this checklist before marking a skill as production-ready.

## Implementation & Testing

- [ ] All tool calls tested with real ToolUniverse instance
- [ ] Test script passes with 100% success
- [ ] Working pipeline runs without errors
- [ ] ALL use cases from SKILL.md tested
- [ ] QUICK_START examples tested (exact copy-paste works)
- [ ] Edge cases tested (invalid inputs, empty results)
- [ ] Result structure validated (all fields present)
- [ ] All parameters tested
- [ ] Error cases handled gracefully
- [ ] SOAP tools have `operation` parameter (if applicable)
- [ ] Fallback strategies implemented and tested
- [ ] Test report created (SKILL_TESTING_REPORT.md)

## Documentation

- [ ] SKILL.md is implementation-agnostic (NO Python/MCP code)
- [ ] python_implementation.py contains working code
- [ ] QUICK_START.md includes both Python SDK and MCP
- [ ] Tool parameter table notes "applies to all implementations"
- [ ] SOAP tool warnings displayed (if applicable)
- [ ] Fallback strategies documented
- [ ] Known limitations documented
- [ ] Example reports referenced
- [ ] Documentation examples verified to work

## Quality

- [ ] Reports are readable (not debug logs)
- [ ] All sections present even if "no data"
- [ ] Source databases clearly attributed
- [ ] Completes in reasonable time (<5 min)
- [ ] Test suite comprehensive (5+ test cases)
- [ ] Test report documents quality metrics
