#!/usr/bin/env perl
# JADE H06 user-side smoke: load the grammar YAML with an independent YAML
# 1.2 loader (Perl YAML::PP, Core schema) and require it to be structurally
# identical to the committed JSON (produced upstream by the npm `yaml`
# package). Usage: yaml_json_parity.pl GRAMMAR.yaml GRAMMAR.json MIN_RULES
use strict;
use warnings;
use JSON::PP ();
use YAML::PP ();
use YAML::PP::Common qw(PRESERVE_ORDER);

my ($yaml_file, $json_file, $min_rules) = @ARGV;
die "usage: $0 GRAMMAR.yaml GRAMMAR.json MIN_RULES\n" unless defined $min_rules;

my $yaml = YAML::PP->new(schema => ['Core'], preserve => PRESERVE_ORDER)->load_file($yaml_file);
open my $fh, '<:raw', $json_file or die "cannot open $json_file: $!\n";
my $json = JSON::PP->new->utf8->decode(do { local $/; <$fh> });

my ($nodes, @diff) = (0);
sub cmp_node {
  my ($y, $j, $path) = @_;
  $nodes++;
  my ($ry, $rj) = (ref $y, ref $j);
  $rj = '' if $rj eq 'JSON::PP::Boolean';
  if ($ry ne $rj) { push @diff, "$path: type yaml=" . ($ry || 'scalar') . " json=" . ($rj || 'scalar'); return }
  if ($ry eq 'HASH') {
    my @ky = keys %$y; my @kj = keys %$j;
    if ("@{[sort @ky]}" ne "@{[sort @kj]}") { push @diff, "$path: key sets differ"; return }
    cmp_node($y->{$_}, $j->{$_}, "$path/$_") for @kj;
    return \@ky;
  }
  if ($ry eq 'ARRAY') {
    if (@$y != @$j) { push @diff, "$path: length yaml=" . @$y . " json=" . @$j; return }
    cmp_node($y->[$_], $j->[$_], "$path\[$_]") for 0 .. $#$j;
    return;
  }
  if (defined $y != defined $j or (defined $y and "$y" ne "$j")) {
    push @diff, "$path: value yaml=" . ($y // 'null') . " json=" . ($j // 'null');
  }
  return;
}
my $top_keys = cmp_node($yaml, $json, '');

# Top-level order must also match: ':NNN' index then its rule, 001..211.
my @rules = grep { /^:\d{3}$/ } @{ $top_keys || [] };
my @expect = map { sprintf ':%03d', $_ } 1 .. scalar @rules;
push @diff, "rule index order differs from 001..N" if "@rules" ne "@expect";

if (@diff) {
  my $shown = @diff > 20 ? 20 : scalar @diff;
  print "::error title=YAML/JSON parity::$_\n" for @diff[0 .. $shown - 1];
  print "::error title=YAML/JSON parity::" . scalar(@diff) . " differences\n";
  exit 1;
}
if (@rules < $min_rules) {
  print "::error title=Zero-test guard::compared " . scalar(@rules) . " rules, expected >= $min_rules\n";
  exit 1;
}
printf "parity OK: rules=%d nodes=%d yaml=%s json=%s\n", scalar(@rules), $nodes, $yaml_file, $json_file;
