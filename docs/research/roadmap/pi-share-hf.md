---
type: research
title: "Pi Share on HuggingFace — Session Export & Publishing"
status: Captured
date: 2026-04-17
source_url: "https://huggingface.co/spaces/badlogic/pi-share"
source_type: product
priority: roadmap
tags: [session-sharing, export, redaction, publishing]
relates_to_adrs: null
---

# Roadmap Research: badlogic/pi-share-hf

## What it is

A tool for collecting, redacting, reviewing, and uploading Pi session files to a Hugging Face dataset.

## Why it should be tracked

The repo is a good reference for a future **session export / curation / publish pipeline** with privacy review and secret scanning in front of publication.

## Why it is not a “now” item

WayWarden should first settle:

- internal session format
- safety and redaction model
- local review workflow
- explicit publish permissions and ownership rules

## Possible future uses

- team-internal replay / research dataset generation
- opt-in fine-tuning or eval corpus generation
- debugging and review bundles
