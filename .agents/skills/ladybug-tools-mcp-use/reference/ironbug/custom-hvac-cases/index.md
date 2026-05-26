# Ironbug Custom HVAC Case Skills

Use this index to select exactly one retained Ironbug custom HVAC case skill when the user request matches a known scenario. Use `../ironbug-custom-hvac-agent-workflows.md` only when the request is a new variant or spans multiple families.
Always read `../ironbug-room-energy-preconditions.md` before the selected case
skill so Room ProgramType, Setpoint, and conditioned-space assumptions are
checked before Ironbug authoring.

Each case skill is intentionally small and scenario-specific. It includes the applicable scene, user prompt/keywords, MCP tool chain, expected MCP return, and short case notes.

## Preconditions

- Start from an existing Garden with a configured base Honeybee Model or
  Dragonfly Model.
- The model must already contain the Rooms needed by the case. Room identifiers
  must match the prompt exactly, such as `Room1`, `Room2`, and `Room5`.
- For current retained 24-case evidence, use the Honeybee DetailedHVAC
  application path unless a future case explicitly records a Dragonfly-retained
  path. Dragonfly is an acceptable prerequisite model family, not an automatic
  claim that every case is Dragonfly-verified.
- Rooms must already have enough Energy setup for simulation. Honeybee Rooms
  must have ProgramType and thermostat Setpoint; if missing, create a Setpoint
  with `energy_create_setpoint(return_object_dict=false)` and pass that target into
  `honeybee_edit_room.setpoint`. For Dragonfly-native hosts, confirm
  conditioned Room2Ds before using `conditioned_only=true`. Reuse a prepared
  weather target when the test Garden already has one.
- The case skill begins at Ironbug HVAC authoring. Do not expand it into
  geometry creation, facade/Radiance work, library authoring, or unrelated
  model setup.

## Scope

The core guidance in each case skill is Ironbug-specific: create source-backed
Ironbug HVAC objects, bind them to matching Rooms through `IB_ThermalZone`,
apply Ironbug DetailedHVAC to the building model, then use the standard Energy
run only as the acceptance check for EUI/ERR/SQL evidence.

## Case Skill Map

| Case | User wording | Case skill |
|---|---|---|
| `ptac_single` | Room1 PTAC | `ptac-single.md` |
| `ptac_two_room` | Room1/Room2 PTAC | `ptac-two-room.md` |
| `pthp_single` | Room1 PTHP | `pthp-single.md` |
| `pthp_two_room` | Room1/Room2 PTHP | `pthp-two-room.md` |
| `unit_heater_single` | unit heater | `unit-heater-single.md` |
| `unit_ventilator_single` | unit ventilator | `unit-ventilator-single.md` |
| `fcu_two_room` | two-room four-pipe FCU | `fcu-two-room.md` |
| `district_fcu_single` | district-cooling FCU | `district-fcu-single.md` |
| `boiler_reheat_single` | boiler hot-water reheat | `boiler-reheat-single.md` |
| `chiller_fcu_single` | chiller/tower FCU | `chiller-fcu-single.md` |
| `fcu_five_room` | five-room four-pipe FCU | `fcu-five-room.md` |
| `doas_only_three_room` | DOAS only | `doas-only-three-room.md` |
| `fcu_doas_three_room` | FCU + DOAS | `fcu-doas-three-room.md` |
| `vrf_single` | single-zone VRF | `vrf-single.md` |
| `vrf_four_room` | four-room VRF | `vrf-four-room.md` |
| `vrf_doas_four_room` | VRF + DOAS | `vrf-doas-four-room.md` |
| `cav_reheat_two_room` | CAV reheat | `cav-reheat-two-room.md` |
| `vav_no_reheat_four_room` | VAV no reheat | `vav-no-reheat-four-room.md` |
| `vav_reheat_four_room` | VAV reheat | `vav-reheat-four-room.md` |
| `unitary_rooftop_three_room` | unitary rooftop | `unitary-rooftop-three-room.md` |
| `dual_loop_fcu_five_room` | FCU with separate hot/chilled loops | `dual-loop-fcu-five-room.md` |
| `chiller_tower_doas_fcu_five_room` | chiller/tower + DOAS + FCU | `chiller-tower-doas-fcu-five-room.md` |
| `primary_secondary_fcu_five_room` | primary/secondary chilled-water FCU | `primary-secondary-fcu-five-room.md` |
| `radiant_doas_three_room` | radiant + cooled DOAS | `radiant-doas-three-room.md` |

## Shared Acceptance

Every case must create Ironbug HVAC through public `create_ironbug_*` tools,
apply with `detailed_hvac_apply_to_honeybee_model`, run standard Energy,
read EUI, and return true `.err` / `.sql` paths. Do not substitute `.ibjson`,
validation, DetailedHVAC object creation, OpenStudio translation, or historical
artifact evidence for a completed Energy run.
