Fs = 60;
l_upper = readmatrix('LeftUpperLeg.csv');
l_lower = readmatrix('LeftLowerLeg.csv');
r_upper = readmatrix('RightUpperLeg.csv');
r_lower = readmatrix('RightLowerLeg.csv');

% Quaternion normalization
l_upper = l_upper ./ vecnorm(l_upper,2,2);
l_lower = l_lower ./ vecnorm(l_lower,2,2);
r_upper = r_upper ./ vecnorm(r_upper,2,2);
r_lower = r_lower ./ vecnorm(r_lower,2,2);
l_upper(:,2:4) = -l_upper(:,2:4);
r_upper(:,2:4) = -r_upper(:,2:4);

% Joint angle calculation
w  = l_upper(:,1).*l_lower(:,1) - l_upper(:,2).*l_lower(:,2) - l_upper(:,3).*l_lower(:,3) - l_upper(:,4).*l_lower(:,4);
xq = l_upper(:,1).*l_lower(:,2) + l_upper(:,2).*l_lower(:,1) + l_upper(:,3).*l_lower(:,4) - l_upper(:,4).*l_lower(:,3);
y  = l_upper(:,1).*l_lower(:,3) - l_upper(:,2).*l_lower(:,4) + l_upper(:,3).*l_lower(:,1) + l_upper(:,4).*l_lower(:,2);
z  = l_upper(:,1).*l_lower(:,4) + l_upper(:,2).*l_lower(:,3) - l_upper(:,3).*l_lower(:,2) + l_upper(:,4).*l_lower(:,1);
l_deg = rad2deg(2 * atan2(vecnorm([xq y z],2,2), abs(w)));
w  = r_upper(:,1).*r_lower(:,1) - r_upper(:,2).*r_lower(:,2) - r_upper(:,3).*r_lower(:,3) - r_upper(:,4).*r_lower(:,4);
xq = r_upper(:,1).*r_lower(:,2) + r_upper(:,2).*r_lower(:,1) + r_upper(:,3).*r_lower(:,4) - r_upper(:,4).*r_lower(:,3);
y  = r_upper(:,1).*r_lower(:,3) - r_upper(:,2).*r_lower(:,4) + r_upper(:,3).*r_lower(:,1) + r_upper(:,4).*r_lower(:,2);
z  = r_upper(:,1).*r_lower(:,4) + r_upper(:,2).*r_lower(:,3) - r_upper(:,3).*r_lower(:,2) + r_upper(:,4).*r_lower(:,1);
r_deg = rad2deg(2 * atan2(vecnorm([xq y z],2,2), abs(w)));

% Autocorrelation (Check)
[acf_l, lag_l] = xcorr(l_deg - mean(l_deg), 'coeff');
[acf_r, lag_r] = xcorr(r_deg - mean(r_deg), 'coeff');
figure
subplot(2,1,1)
plot(lag_l/Fs, acf_l, 'b')
title('Left Knee Autocorrelation')
grid on
subplot(2,1,2)
plot(lag_r/Fs, acf_r, 'r')
title('Right Knee Autocorrelation')
grid on

% Local maxima
[l_pks, l_locs] = findpeaks(l_deg, ...
'MinPeakDistance', round(0.5*Fs), ...
'MinPeakProminence', 5);
[r_pks, r_locs] = findpeaks(r_deg, ...
'MinPeakDistance', round(0.5*Fs), ...
'MinPeakProminence', 5);

% Peak to peak local minima
l_minloc = [];
l_minval = [];
for i = 1:length(l_locs)-1
startIdx = l_locs(i);
endIdx   = l_locs(i+1);
segment = l_deg(startIdx:endIdx);
invSeg = -segment;
[~, locs] = findpeaks(invSeg);
if ~isempty(locs)
minIdx = startIdx + locs(1) - 1;
l_minloc(end+1,1) = minIdx;
l_minval(end+1,1) = l_deg(minIdx);
end
end
r_minloc = [];
r_minval = [];
for i = 1:length(r_locs)-1
startIdx = r_locs(i);
endIdx   = r_locs(i+1);
segment = r_deg(startIdx:endIdx);
invSeg = -segment;
[~, locs] = findpeaks(invSeg);
if ~isempty(locs)
minIdx = startIdx + locs(1) - 1;
r_minloc(end+1,1) = minIdx;
r_minval(end+1,1) = r_deg(minIdx);
end
end

% Visual check
figure; hold on
plot(l_deg,'k')
plot(l_locs,l_deg(l_locs),'ro')
plot(l_minloc,l_minval,'bo')
title('Left Knee: Peaks (red) + First Minima (blue)')
grid on

% Cycle identification
l_cycles = cell(length(l_minloc)-1,1);
r_cycles = cell(length(r_minloc)-1,1);
for i = 1:length(l_minloc)-1
l_cycles{i} = l_deg(l_minloc(i):l_minloc(i+1));
end
for i = 1:length(r_minloc)-1
r_cycles{i} = r_deg(r_minloc(i):r_minloc(i+1));
end

%Cycle normalization
N = 100;
l_mat = nan(length(l_cycles),N);
r_mat = nan(length(r_cycles),N);
for i = 1:length(l_cycles)
c = l_cycles{i};
x = linspace(0,1,length(c));
xi = linspace(0,1,N);
l_mat(i,:) = interp1(x,c,xi);
end
for i = 1:length(r_cycles)
c = r_cycles{i};
x = linspace(0,1,length(c));
xi = linspace(0,1,N);
r_mat(i,:) = interp1(x,c,xi);
end
t = linspace(0,100,N);

% Variability metrics
l_mean = mean(l_mat,1,'omitnan');
r_mean = mean(r_mat,1,'omitnan');
l_std  = std(l_mat,0,1,'omitnan');
r_std  = std(r_mat,0,1,'omitnan');
l_min = min(l_mat,[],1);
l_max = max(l_mat,[],1);
r_min = min(r_mat,[],1);
r_max = max(r_mat,[],1);

% Figure 1: Mean and std
figure; hold on
f1 = fill([t fliplr(t)], [l_mean+l_std fliplr(l_mean-l_std)], ...
'b','FaceAlpha',0.25,'EdgeColor','none');
f2 = fill([t fliplr(t)], [r_mean+r_std fliplr(r_mean-r_std)], ...
'r','FaceAlpha',0.25,'EdgeColor','none');
h1 = plot(t,l_mean,'b','LineWidth',2);
h2 = plot(t,r_mean,'r','LineWidth',2);
legend([f1 f2 h1 h2], ...
{'Left ± STD','Right ± STD','Left Mean','Right Mean'}, ...
'Location','best')
title('Mean ± STD (Min-to-Min Cycles)')
xlabel('Gait Cycle (%)')
ylabel('Angle (deg)')
grid on

% Figure 2: Mean and variability
figure; hold on
f1 = fill([t fliplr(t)], [l_max fliplr(l_min)], ...
'b','FaceAlpha',0.15,'EdgeColor','none');
f2 = fill([t fliplr(t)], [r_max fliplr(r_min)], ...
'r','FaceAlpha',0.15,'EdgeColor','none');
h1 = plot(t,l_mean,'b','LineWidth',2);
h2 = plot(t,r_mean,'r','LineWidth',2);
legend([f1 f2 h1 h2], ...
{'Left Envelope','Right Envelope','Left Mean','Right Mean'}, ...
'Location','best')
title('Envelope Variability')
grid on

% Figure 3: Heatmap
figure
subplot(2,1,1)
imagesc(l_mat)
colorbar
title('Left Knee Cycles')
subplot(2,1,2)
imagesc(r_mat)
colorbar
title('Right Knee Cycles')