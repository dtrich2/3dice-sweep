#!/usr/bin/perl

use strict;
use Cwd;

my $root_path = $ENV{'DV_ROOT'}.'/design/sys/iop/spc';
my $cwd = cwd();


my @list = ('dec', 'exu', 'fgu', 'gkt', 'ifu/ifu_cmu', 'ifu/ifu_ftu', 'ifu/ifu_ibu', 'lsu', 'mmu', 'pku', 'pmu', 'tlu');

print "{";
foreach my $mod (@list){
	my $dir = $root_path.'/'.$mod.'/synopsys';
	$mod =~ s/^.*\///;
	my $areafile = $dir.'/log/'.$mod.'_area.rep';
	my $powerfile = $dir.'/log/'.$mod.'_power.rep';
	chdir($dir) or die "Can't Change Directory to $dir";
	my $area = `grep "Total cell area:" $areafile`;
	chomp $area;
	$area =~ s/Total cell area:\s*//;
	my $power = `grep "Total      " $powerfile`;
	chomp $power;
	$power =~ s/Total(.*)W\s\s\s\s\s//;
	$power =~ s/\suW$//;
	print "'", $mod, "': {'power': " , $power, ", 'area': ", $area, "},\n";
}
print "\n";
