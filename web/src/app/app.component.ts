import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDrawerMode, MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatBadgeModule } from '@angular/material/badge';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Document, SentinelService, User } from './sentinel.service';
import { switchMap } from 'rxjs/operators';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    FormsModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatBadgeModule,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  opened = true;
  mode: MatDrawerMode = 'side';
  documentCount = 0;
  documents: Document[] = [];
  loaded = false;
  users: User[] = [];
  userKey?: string;

  constructor(private sentinelService: SentinelService) {}

  ngOnInit(): void {
    this.sentinelService.getUsers().subscribe((response) => {
      this.users = response.data;
      this.userKey = this.users.find((user) => user.role === 'user')?.key;

      this.loaded = true;
    });

    this.sentinelService
      .getUsers()
      .pipe(
        switchMap((response) => {
          this.users = response.data;
          this.userKey = this.users[0].key;
          return this.sentinelService.getDocuments(this.userKey);
        })
      )
      .subscribe({
        next: (response) => {
          this.documentCount = response.length;

          // Sort documents by sensitivity (low > medium > high)
          this.documents = response.sort((a, b) => {
            const sensitivityOrder: { [key: string]: number } = {
              low: 1,
              medium: 2,
              high: 3,
            };
            return (
              sensitivityOrder[a.sensitivity] - sensitivityOrder[b.sensitivity]
            );
          });
        },
        complete: () => {
          this.loaded = true;
        },
      });
  }

  toggleSidenav() {
    this.opened = !this.opened;
  }

  onUserChange(userKey: string) {
    this.sentinelService.getDocuments(userKey).subscribe((response) => {
      this.documentCount = response.length;

      // Sort documents by sensitivity (low > medium > high)
      this.documents = response.sort((a, b) => {
        const sensitivityOrder: { [key: string]: number } = {
          low: 1,
          medium: 2,
          high: 3,
        };
        return (
          sensitivityOrder[a.sensitivity] - sensitivityOrder[b.sensitivity]
        );
      });
    });
  }
}
