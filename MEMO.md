# Memo
- 2020/04/21/Mon
  - systemdに登録し、自動起動のサービス化するスクリプトを書いた。
  - READMEに、超簡単Usageを書いた。

- 2020/04/13/Mon
  - https://qiita.com/tinoue@github/items/7831849e6a9560159fa5
  - `dphys-swapfile`はpurgeしちゃった
  - tmpfs化は`/tmp`と`/var/tmp`だけ、`/var/log`はほんのり面倒だから。

- 2020/04/11/sat
  - せっかくだからプロパティの実装が気持ち整然とする、`dataclass`を使ってみようと思ったけど、開発PCがUbuntu16.04LTSだと、Python3.7が、apt一発ではなくソースからインストールになる。
  - https://tecadmin.net/install-python-3-7-on-ubuntu-linuxmint/
    見たら、意外と楽そう。
  - https://mu-777.hatenablog.com/entry/2020/03/07/195833
    もっと楽な方法があったので、こっちでやった。