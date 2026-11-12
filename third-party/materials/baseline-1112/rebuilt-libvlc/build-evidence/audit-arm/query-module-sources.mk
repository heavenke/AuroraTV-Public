.PHONY: aurora-module-inventory
aurora-module-inventory:
	$(file >/mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/audit-arm/selected-module-sources.tsv,)
	$(foreach module,$(LTLIBRARIES),$(file >>/mnt/d/AI_PROJECT/AuroraTV/artifacts/vlc-lgpl-build/audit-arm/selected-module-sources.tsv,$(module)|$($(subst .,_,$(subst -,_,$(notdir $(module))))_SOURCES)|$(nodist_$(subst .,_,$(subst -,_,$(notdir $(module))))_SOURCES)|$($(subst .,_,$(subst -,_,$(notdir $(module))))_LIBADD)))
	@true
