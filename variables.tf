variable "observe_customer" {
  type        = string
  description = "Observe customer id"
}

variable "observe_token" {
  type        = string
  description = "Observe ingest token"
}

variable "observe_domain" {
  type        = string
  description = "Observe domain"
  default     = "observeinc.com"
}

# Based on NCRONTAB Expressions
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-csharp#ncrontab-expressions

variable "timer_resources_func_schedule" {
  type        = string
  description = "Eventhub name to use for resources function"
  default     = "0 */10 * * * *"
}

variable "timer_vm_metrics_func_schedule" {
  type        = string
  description = "Eventhub name to use for vm metrics function"
  default     = "30 */5 * * * *"
}

variable "func_url" {
  type        = string
  description = "Observe Collect Function source URL zip"
  default     = "https://observeinc.s3.us-west-2.amazonaws.com/azure/azure-collection-functions-v0.1.0.zip"
}

# Use Name for value
# https://azuretracks.com/2021/04/current-azure-region-names-reference/

variable "location" {
  type        = string
  description = "Azure Location to deploy resources"
  default     = "eastus"
}

variable "location_abbreviation" {
  type        = map(string)
  description = "A unique, short abbreviation to use for each location when assiging names to resources"
  default = {
    "australiacentral" : "ac",
    "australiacentral2" : "ac2",
    "australiaeast" : "ae",
    "asiapacific" : "ap",
    "australia" : "as",
    "australiasoutheast" : "ase",
    "brazil" : "b",
    "brazilsouth" : "bs",
    "brazilsoutheast" : "bse",
    "canada" : "c",
    "canadacentral" : "cc",
    "canadaeast" : "ce",
    "centralindia" : "ci",
    "centralus" : "cu",
    "centraluseuap" : "cue",
    "centralusstage" : "cus",
    "europe" : "e",
    "eastasia" : "ea",
    "eastasiastage" : "eas",
    "eastus" : "eu",
    "eastus2" : "eu2",
    "eastus2euap" : "eu2e",
    "eastus2stage" : "eu2s",
    "eastusstage" : "eus",
    "eastusstg" : "eustg",
    "france" : "f",
    "francecentral" : "fc",
    "francesouth" : "fs",
    "germany" : "g",
    "global" : "glob",
    "germanynorth" : "gn",
    "germanywestcentral" : "gwc",
    "india" : "i",
    "japan" : "j",
    "japaneast" : "je",
    "jioindiacentral" : "jic",
    "jioindiawest" : "jiw",
    "japanwest" : "jw",
    "korea" : "k",
    "koreacentral" : "kc",
    "koreasouth" : "ks",
    "norway" : "n",
    "northcentralus" : "ncu",
    "northcentralusstage" : "ncus",
    "northeurope" : "ne",
    "norwayeast" : "nwe",
    "norwaywest" : "nww",
    "qatarcentral" : "qc",
    "singapore" : "s",
    "southafrica" : "sa",
    "southafricanorth" : "san",
    "southeastasiastage" : "sas",
    "southafricawest" : "saw",
    "swedencentral" : "sc",
    "southcentralus" : "scu",
    "southcentralusstage" : "scus",
    "southcentralusstg" : "sctg",
    "southeastasia" : "sea",
    "southindia" : "si",
    "switzerlandnorth" : "sn",
    "switzerlandwest" : "sw",
    "switzerland" : "sz",
    "uae" : "uae",
    "uaecentral" : "uc",
    "uk" : "uk",
    "uaenorth" : "un",
    "uksouth" : "us",
    "unitedstates" : "us",
    "unitedstateseuap" : "use",
    "ukwest" : "uw",
    "westcentralus" : "wcu",
    "westeurope" : "we",
    "westindia" : "wi",
    "westus" : "wu",
    "westus2" : "wu2",
    "westus2stage" : "wu2s",
    "westus3" : "wu3",
    "westusstage" : "wus",
  }
}
