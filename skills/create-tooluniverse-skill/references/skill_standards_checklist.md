# Skill Standards Checklist

Complete checklist for validating ToolUniverse skills before release.

## Implementation & Testing

### Tool Verification
- [ ] All tools tested with real ToolUniverse instance (CRITICAL)
- [ ] Test script created BEFORE documentation
- [ ] Tool parameters verified (not assumed from function names)
- [ ] Response formats documented (standard, direct list, direct dict)
- [ ] SOAP tools have `operation` parameter (if applicable)
- [ ] Parameter corrections table included

### Testing
- [ ] Test script passes (`test_[skill].py`)
- [ ] 100% test success rate
- [ ] Working pipeline runs without errors
- [ ] 2-3 complete examples tested end-to-end
- [ ] Error cases handled gracefully
- [ ] Empty data scenarios tested
- [ ] API failures tested

### Error Handling
- [ ] Fallback strategies implemented
- [ ] Primary → Fallback → Default pattern used
- [ ] Try/except blocks for each database
- [ ] Clear error messages in reports
- [ ] Continues if one phase fails
- [ ] Notes unavailable data explicitly

---

## Documentation

### SKILL.md (Implementation-Agnostic)
- [ ] NO Python/MCP code in SKILL.md (CRITICAL)
- [ ] Describes WHAT to do, not HOW in specific language
- [ ] Tool names listed
- [ ] Parameters described conceptually
- [ ] Decision logic documented
- [ ] Workflow phases clearly structured
- [ ] Fallback strategies documented
- [ ] Tool parameter reference table included
- [ ] Response format notes included
- [ ] Limitations section present

### python_implementation.py
- [ ] Complete working pipeline
- [ ] Uses only tested tools
- [ ] Error handling for each phase
- [ ] Progressive report writing
- [ ] Clear status messages
- [ ] Example usage in `if __name__ == "__main__"`
- [ ] Docstrings for all functions
- [ ] Type hints where appropriate

### QUICK_START.md
- [ ] Both Python SDK and MCP sections
- [ ] Equal treatment of both interfaces
- [ ] Concrete examples for both
- [ ] Tool parameter table notes "applies to all implementations"
- [ ] Common recipes in both formats
- [ ] Troubleshooting section
- [ ] Expected output examples
- [ ] Next steps section

### test_skill.py
- [ ] Tests each input type
- [ ] Tests combined inputs
- [ ] Verifies report sections exist
- [ ] Checks error handling
- [ ] Returns proper exit codes
- [ ] Clear test names and descriptions

---

## Quality Standards

### Code Quality
- [ ] No hardcoded values (use parameters)
- [ ] Proper error messages
- [ ] Clean, readable code
- [ ] No debug print statements (except intentional status)
- [ ] Follows Python conventions
- [ ] No security vulnerabilities

### Report Quality
- [ ] Reports are readable (not debug logs)
- [ ] All sections present even if "no data"
- [ ] Source databases clearly attributed
- [ ] Proper markdown formatting
- [ ] Tables formatted consistently
- [ ] No raw tool outputs dumped

### Performance
- [ ] Completes in reasonable time (<5 min for basic examples)
- [ ] No unnecessary API calls
- [ ] Efficient data processing
- [ ] Progress updates at appropriate intervals

---

## Content Completeness

### Required Sections in SKILL.md
- [ ] YAML frontmatter (name + description)
- [ ] When to Use This Skill
- [ ] Core Databases Integrated table
- [ ] Workflow Overview diagram
- [ ] Phase descriptions for each step
- [ ] Tool Parameter Reference
- [ ] Response Format Notes
- [ ] Fallback Strategies
- [ ] Limitations & Known Issues
- [ ] Summary

### Required Files
- [ ] SKILL.md
- [ ] python_implementation.py
- [ ] QUICK_START.md
- [ ] test_skill.py

### Optional But Recommended
- [ ] Example output reports
- [ ] Additional test cases
- [ ] Performance benchmarks
- [ ] Known issues documentation

---

## User Testing

### Fresh Environment Test
- [ ] Load ToolUniverse in new environment
- [ ] Import python_implementation
- [ ] Run example from QUICK_START
- [ ] Verify output matches expectations
- [ ] No unexpected errors

### Documentation Test
- [ ] Another person can follow QUICK_START
- [ ] Examples work without modification
- [ ] Parameter descriptions are clear
- [ ] Troubleshooting helps resolve issues

### MCP Test
- [ ] Conversational examples work
- [ ] Direct tool calls work
- [ ] Parameter names match SDK
- [ ] Results are equivalent to SDK

---

## Integration Standards

### Compatibility
- [ ] Works with current ToolUniverse version
- [ ] No deprecated tool usage
- [ ] Python version compatibility noted
- [ ] Required packages documented

### Integration with Other Skills
- [ ] devtu-create-tool referenced if tools needed
- [ ] devtu-fix-tool referenced for debugging
- [ ] devtu-optimize-skills principles applied
- [ ] Related skills cross-referenced

---

## SOAP Tools (If Applicable)

- [ ] SOAP tools identified in testing
- [ ] `operation` parameter added to all SOAP calls
- [ ] SOAP tools prominently noted in documentation
- [ ] Side-by-side Python/MCP examples for SOAP tools
- [ ] Warning in QUICK_START about operation parameter

Example SOAP tools: IMGT_*, SAbDab_*, TheraSAbDab_*

---

## Fallback Strategies (If Applicable)

For skills with external APIs:
- [ ] Primary tool identified
- [ ] Fallback tool identified
- [ ] Default behavior defined
- [ ] Fallback documented in SKILL.md
- [ ] Fallback implemented in python_implementation.py
- [ ] Fallback tested

---

## Before Release

### Final Checks
- [ ] All tests pass 100%
- [ ] Documentation reviewed for typos
- [ ] Examples verified to work
- [ ] Files in correct locations
- [ ] No unnecessary files included
- [ ] No sensitive information in code/docs

### Summary Document
- [ ] Create NEW_SKILL_[DOMAIN].md
- [ ] Document key features
- [ ] List tools integrated
- [ ] Show test results
- [ ] Note any limitations
- [ ] Suggest future enhancements

---

## Post-Release

### Monitoring
- [ ] Track usage patterns
- [ ] Collect user feedback
- [ ] Note common issues
- [ ] Identify improvement opportunities

### Maintenance
- [ ] Update when tools change
- [ ] Fix reported bugs
- [ ] Add requested features
- [ ] Keep documentation current

---

## Red Flags (Must Fix Before Release)

❌ **CRITICAL - Documentation before testing**
- Tools not tested with real API calls
- Parameters assumed from function names
- Response formats not verified

❌ **CRITICAL - Implementation-specific SKILL.md**
- Python code in SKILL.md
- MCP prompts in SKILL.md
- Single implementation focus

❌ **CRITICAL - No error handling**
- No try/except blocks
- No fallback strategies
- Fails completely if one tool errors

❌ **Test failures**
- Tests don't pass 100%
- Tests not written
- Tests never run

❌ **Incomplete documentation**
- Missing QUICK_START
- No MCP examples
- Parameter table missing

❌ **SOAP tools broken**
- Missing `operation` parameter
- No warning in docs
- Untested SOAP calls

---

## Success Metrics

**High-quality skill has**:
- ✅ 100% test coverage
- ✅ Implementation-agnostic SKILL.md
- ✅ Multi-implementation QUICK_START
- ✅ Complete error handling
- ✅ Tool parameters verified
- ✅ Response formats documented
- ✅ Fallback strategies implemented
- ✅ All files present and correct

**Quality score**: Count checkboxes above ÷ total checkboxes

**Target**: ≥95% before release
