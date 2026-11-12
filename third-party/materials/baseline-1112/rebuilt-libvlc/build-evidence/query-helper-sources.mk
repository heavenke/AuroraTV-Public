.PHONY: aurora-helper-inventory
AURORA_INVENTORY_TARGET_FILE ?= /mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/helper-module-sources-arm64.tsv
aurora-helper-inventory:
	$(file >$(AURORA_INVENTORY_TARGET_FILE),)
	$(foreach variable,$(filter %_la_SOURCES,$(.VARIABLES)),$(file >>$(AURORA_INVENTORY_TARGET_FILE),$(variable)|$($(variable))|$($(patsubst %_SOURCES,%_LIBADD,$(variable)))))
	@true
