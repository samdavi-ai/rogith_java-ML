# RecoLens class taxonomy (Phase 8 proposal)

Status date: 2026-10-02. This is a product taxonomy proposal, not a claim that model v1 supports the proposed labels. Model v1 stays unchanged with its existing six-label output mapping.

## System-level result vs model class

`E_WASTE`, `NOT_E_WASTE`, and `UNKNOWN` are system decisions, not necessarily neural-network labels. A category model can predict `charger_adapter`; a separately evaluated system decision maps a supported electronic category to `E_WASTE`. `NOT_E_WASTE` requires positive evidence from a trained, calibrated rejection stage. `UNKNOWN` covers low confidence, conflicting stages, unsupported electronic items, and out-of-distribution input. A six-class forced prediction is not evidence that an object is electronic.

## Proposed class inventory

Image counts below are source-counts in the existing 2,157-image CC BY 4.0 dataset; these are not necessarily unique physical objects. New-source counts are stated only when source documentation provides them; unknown means not established, not zero.

| Class | RecoLens need | Available data | Visual distinction / ambiguity | Evaluation available | Decision |
|---|---|---|---|---|---|
| battery | Existing supported object; safe recycling guidance | 148 source images in current archive; Bower validation candidate has 53 unique Battery images | Visually varied shapes/chemistries; can resemble generic metal/plastic | Existing 15-item test support; Bower subset still needs privacy review | APPROVED (v1) |
| keyboard | Existing supported object | 126 source images | Distinct at whole-object scale; laptop keyboard scenes create partial-object ambiguity | Existing 8-item test support | APPROVED (v1) |
| light bulb | Existing supported object | 43 source images | Glass bulbs vary; bulb vs clear container and LED fixtures can overlap | Existing 3-item test support is very small; Bower downloaded annotations had no `Bulb` object examples | APPROVED (v1) |
| phone | Existing supported object | 151 source images | Phone/tablet/device images may be small or occluded | Existing 12-item test support | APPROVED (v1) |
| mouse | Existing supported object | 80 source images | Small peripheral; bottle/base silhouettes can confuse | Existing 6-item test support | APPROVED (v1) |
| PCB | Existing supported object | 205 source images | Circuit boards vary; may appear as components in other devices | Existing 16-item test support | APPROVED (v1) |
| charger_adapter | Needed for observed adapter misclassification | No explicit class in current source; Bower only labels generic `Electronic device` / `Electronic Waste`; GIZ has no charger class | Charger vs AC adapter often not visually separable from exterior alone; combine until evidence supports two labels | User adapter screenshot crop is one qualitative case | PROPOSED; data gate not met |
| laptop | Needed to avoid interpreting whole laptops as keyboards | GIZ labels Laptops/Computers, but count not independently audited; Mendeley CC BY 4.0 laptop-component dataset has 3,640 raw images of disassembled components, not intact laptops | Whole laptop vs standalone keyboard depends on scene framing and visible display; Laptop/Computer hierarchy needs consistent labels | One user laptop/keyboard scene only | PROPOSED; data gate not met |
| monitor_display | Common discarded electronics category | GIZ `Computers` may be broad; laptop-parts Mendeley source lists internal LCDScreen parts, not standalone monitors; no independently audited whole-monitor count | Screen-only photo can be TV, monitor, laptop, or display panel | None in local locked set | DEFERRED |
| cable | Common e-waste accessory | Laptop-parts Mendeley source lists DCCable/LVDSCable at 140 raw images each, but these are internal laptop cables and the archive is not audited | Cable vs ordinary wire/rope and bundled clutter is ambiguous | None in local locked set | DEFERRED |
| earphones_headphones | Common accessory | No explicit count in audited sources | Earbuds, wired earphones, headphones and cables differ in scale | None | DEFERRED |
| other_electronic | Catchall to avoid sending every unseen device to non-e-waste | Broad GIZ categories and Bower generic electronic device labels are not a stable whole-item class dataset | Extremely broad visual category; can swallow unsupported objects and conceal subtype errors | Bower supports broad electronic waste vs household-item evaluation only | DEFERRED until taxonomy has a reject path and subtype data |
| not_e_waste | Must reject bottles, paper and household objects | Existing Mendeley labels include plastic, glass, paper and organic waste; previous candidate used 597 train / 113 validation / 115 test images across four negative source classes | Excluded source classes may not represent all household objects; metal/medical labels ambiguous | Prior negative-class candidate split; user bottle crop; Bower dataset is a possible phone-photo external benchmark | PROPOSED system state, not an electronics subtype |

## Current support boundary

Production model v1.0.0 supports only the six approved rows shown above. Charger/adapter, laptop, monitor, cable, earphones/headphones and other electronic device are not supported categories. Until class data, versioned annotation, and a locked category-specific test are available, the safe system-level result for these objects is `UNKNOWN`, not a forced category or `NOT_E_WASTE`.
