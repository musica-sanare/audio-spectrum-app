<!-- source: docs/en/README.md blob 2dccd7f44b78a47edd6f855b0eb9e2c1ee3e9494 -->
[English](../en/README.md) | 日本語 · [リポジトリの README](../../README.ja.md)

> この文書は[英語版](../en/README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# audio-spectrum-app ドキュメント

オフラインのオーディオスペクトラム動画レンダラーの仕様・設計・開発方法と、各フェーズの記録です。

## ガイド

| 文書 | 説明 |
|---|---|
| [ユーザーガイド](USER_GUIDE.md) | セットアップ、普段の使い方、コマンドリファレンス、プリセット、ほかのツールからの利用（JSON イベント、Python API）。 |
| [開発](DEVELOPMENT.md) | セットアップ、テスト、見た目の確認、規約。 |

## 設計

| 文書 | 説明 |
|---|---|
| [アーキテクチャ](ARCHITECTURE.md) | 層構成、データの流れ、守るべき不変条件、性能、拡張ポイント。 |

## 作業用ドキュメント（英語のみ）

| 文書 | 説明 |
|---|---|
| [Requirements](../working/REQUIREMENTS.md)（英語のみ） | 目的、範囲、機能要件と非機能要件、技術選定。 |
| [Decisions](../working/DECISIONS.md)（英語のみ） | 設計判断の記録（ADR）。 |
| [Phase 0 plan](../working/PHASE0_PLAN.md)（英語のみ） | リポジトリの土台と試作：解析、描画、書き出し、同期。 |
| [Phase 0 results](../working/PHASE0_RESULTS.md)（英語のみ） | Phase 0 の測定結果：描画ライブラリ、速度、同期、キーイング。 |
| [Phase 1 plan](../working/PHASE1_PLAN.md)（英語のみ） | MVP CLI：プリセットのファイル化、CLI の約束事（一括処理、進捗、終了コード）、公開 API、正式な文書。 |
| [Phase 1 acceptance](../working/PHASE1_ACCEPTANCE.md)（英語のみ） | Phase 1 の受入報告：完了条件、要件の充足状況、測定値、次の候補。 |
